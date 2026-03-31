"""
Ring attractor simulation - dopamine modulation of working memory stability.

D1 activation scales recurrent excitation (da parameter).
High DA: deep attractor well, bump resists distractors.
Low DA: shallow well, competing stimulus can capture the bump.
"""

from brian2 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

start_scope()

N  = 100
tau  = 15*ms
tau_syn = 5*ms
v_rest = -70*mV
v_thr = -50*mV
v_reset = -70*mV
J_e   = 7.0
J_i  = 0.2
sig_e  = 0.05
noise   = 0.9*mV

CUE_CENTER = 50
DIST_CENTER = (CUE_CENTER + N//2) % N
CUE_HW   = 5

da_levels = [1.0, 0.88, 0.78]
da_labels = ['high DA\n(healthy)', 'moderate DA\n(fatigued)', 'low DA\n(depleted)']
da_colors = ['#4fc97e', '#f5a623', "#e05e5e"]


def ring_dist(a, b, n=N):
    d = np.abs(np.asarray(a) - np.asarray(b))
    return np.minimum(d, n - d)


def run_condition(da):
    start_scope()
    np.random.seed(7)

    eqs = '''
    dv/dt  = (v_rest - v + I_bg + I_ext + g_syn + xi*noise*tau**0.5) / tau : volt (unless refractory)
    dg_syn/dt = -g_syn / tau_syn : volt
    I_bg  : volt
    I_ext : volt
    '''

    G = NeuronGroup(N, eqs,
                    threshold='v > v_thr',
                    reset='v = v_reset',
                    refractory=2*ms,
                    method='euler')
    G.v    = v_rest + np.random.uniform(-2, 0, N)*mV
    G.I_bg = 15*mV

    S = Synapses(G, G, 'w : volt', on_pre='g_syn_post += w')
    S.connect()

    d_norm = ring_dist(np.array(S.i), np.array(S.j)) / N
    S.w = (da * J_e * np.exp(-0.5 * (d_norm / sig_e)**2) - J_i) * mV

    spikes = SpikeMonitor(G)
    vmem = StateMonitor(G, 'v', record=True)

    run(50*ms)

    r = ring_dist(np.arange(N), CUE_CENTER)
    G.I_ext = np.where(r <= CUE_HW, 12.0, 0.0) * mV
    run(100*ms)

    G.I_ext = 0*mV
    run(80*ms)

    # distractor on the opposite side of the ring, half the cue amplitude
    r2 = ring_dist(np.arange(N), DIST_CENTER)
    G.I_ext = np.where(r2 <= CUE_HW, 4.0, 0.0) * mV
    run(30*ms)

    G.I_ext = 0*mV
    run(40*ms)

    return spikes, vmem


def circular_centroid(spike_times, spike_ids, t0, t1, n=N):
    mask = (spike_times >= t0) & (spike_times < t1)
    ids  = spike_ids[mask].astype(float)
    if len(ids) == 0:
        return np.nan
    ang = 2 * np.pi * ids / n
    return (np.arctan2(np.mean(np.sin(ang)), np.mean(np.cos(ang))) / (2*np.pi) * n) % n


def bump_centroids(spikes, win=10, step=5, t_start=50, t_end=300):
    st = spikes.t / ms
    si = np.array(spikes.i, dtype=float)
    t_wins = np.arange(t_start, t_end - win, step)
    return t_wins, np.array([circular_centroid(st, si, t, t + win) for t in t_wins])


results = [run_condition(da) for da in da_levels]

fig = plt.figure(figsize=(16, 11))
fig.patch.set_facecolor('#0d0d0d')
gs_top = gridspec.GridSpec(1, 3, figure=fig, top=0.88, bottom=0.55, wspace=0.3)
gs_bot = gridspec.GridSpec(1, 3, figure=fig, top=0.47, bottom=0.09, wspace=0.3)

T_TOTAL = 300
BIN_MS  = 5
N_BINS = T_TOTAL // BIN_MS


def style_ax(ax):
    ax.set_facecolor('#0d0d0d')
    ax.tick_params(colors='#aaaaaa', labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor('#2a2a2a')


def epoch_lines(ax):
    for x, c in [(50, '#4fc97e'), (150, '#4c9be8'), (230, '#f5a623'), (260, '#f5a623')]:
        ax.axvline(x, color=c, lw=0.9, linestyle='--', alpha=0.65)


for col, (da, label, col_color, (sp, vm)) in enumerate(
        zip(da_levels, da_labels, da_colors, results)):

    st = sp.t / ms
    si = np.array(sp.i, dtype=float)

    rate_map = np.zeros((N, N_BINS))
    for t_sp, i_sp in zip(st, si):
        b = int(t_sp / BIN_MS)
        if 0 <= b < N_BINS:
            rate_map[int(i_sp), b] += 1

    ax_h = fig.add_subplot(gs_top[0, col])
    style_ax(ax_h)
    ax_h.imshow(rate_map, aspect='auto', origin='lower',
                extent=[0, T_TOTAL, 0, N],
                cmap='inferno', interpolation='bilinear',
                vmin=0, vmax=max(rate_map.max(), 1) * 0.9)
    epoch_lines(ax_h)
    ax_h.set_xlim(0, T_TOTAL)
    ax_h.set_ylim(0, N)
    ax_h.set_title(label, color=col_color, fontsize=10, pad=5)
    ax_h.set_xlabel('time (ms)', color='#888888', fontsize=8)
    if col == 0:
        ax_h.set_ylabel('neuron', color='#888888', fontsize=8)
    else:
        ax_h.set_yticklabels([])

    t_w, cents = bump_centroids(sp)
    valid = ~np.isnan(cents)

    ax_d = fig.add_subplot(gs_bot[0, col])
    style_ax(ax_d)
    if valid.any():
        ax_d.plot(t_w[valid], cents[valid], color=col_color, lw=1.8, alpha=0.9)
        ax_d.scatter(t_w[valid], cents[valid], s=14, color=col_color,
                     zorder=3, edgecolors='none')
    ax_d.axhline(CUE_CENTER,  color='#4fc97e', lw=1, linestyle=':', alpha=0.8,
                 label=f'cue ({CUE_CENTER})')
    ax_d.axhline(DIST_CENTER, color='#f5a623', lw=1, linestyle=':', alpha=0.8,
                 label=f'distractor ({DIST_CENTER})')
    epoch_lines(ax_d)
    ax_d.set_xlim(50, T_TOTAL)
    ax_d.set_ylim(0, N)
    ax_d.set_xlabel('time (ms)', color='#888888', fontsize=8)
    if col == 0:
        ax_d.set_ylabel('bump centroid', color='#888888', fontsize=8)
        ax_d.legend(fontsize=7, facecolor='#1a1a1a', labelcolor='#bbbbbb',
                    edgecolor='#333333', loc='upper left')
    else:
        ax_d.set_yticklabels([])

    post_c = circular_centroid(st, si, 265, 295)
    shift  = post_c - CUE_CENTER if not np.isnan(post_c) else None
    n_late = int(np.sum((st > 250) & (st < 300)))
    c_str  = f"{post_c:.1f}  offset: {shift:+.1f}" if shift is not None else "NaN  (bump collapsed)"
    print(f"DA={da:.2f}  |  late spikes: {n_late:3d}  |  centroid: {c_str}")

legend_items = [
    plt.Line2D([0], [0], color='#4fc97e', lw=1.2, linestyle='--', label='cue on (50 ms)'),
    plt.Line2D([0], [0], color='#4c9be8', lw=1.2, linestyle='--', label='cue off (150 ms)'),
    plt.Line2D([0], [0], color='#f5a623', lw=1.2, linestyle='--', label='distractor (230–260 ms)'),
]
fig.legend(handles=legend_items, loc='upper center', ncol=3,
           facecolor='#1a1a1a', labelcolor='#cccccc', edgecolor='#333333',
           fontsize=9, bbox_to_anchor=(0.5, 0.955))

fig.text(0.5, 0.99,
         'Dopamine-Modulated Working Memory - Distractor Resistance in a Ring Attractor',
         ha='center', va='top', color='#eeeeee', fontsize=12, fontweight='bold')
fig.text(0.5, 0.505,
         'bump centroid over time  (circular mean of active neurons)',
         ha='center', va='bottom', color='#666666', fontsize=8.5)

plt.savefig('ring_attractor_dopamine.png', dpi=150,
            bbox_inches='tight', facecolor=fig.get_facecolor())