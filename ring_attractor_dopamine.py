"""
Ring attractor + dopamine gain modulation.

D1 activation scales recurrent excitation via a single parameter (da).
Below a threshold (~0.79), the bump cannot persist during the delay
period, even without a distractor. Above it, the bump survives and
resists distractors.

"""

from brian2 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import os
import time

prefs.codegen.target = 'numpy'
start_scope()

OUT_DIR = os.path.dirname(os.path.abspath(__file__)) or '.'

N = 100
tau = 15 * ms
tau_syn = 5 * ms
v_rest = -70 * mV
v_thr = -50 * mV
v_reset = -70 * mV

J_e = 7.0
J_i = 0.2
sig_e = 0.05
noise_amp = 0.9 * mV

CUE_CENTER = 50
DIST_CENTER = (CUE_CENTER + N // 2) % N
CUE_HW = 5
CUE_AMP = 12.0
DIST_AMP = 4.0  # set to 0 for control

da_vals = np.unique(np.concatenate([
    np.round(np.arange(0.70, 0.78, 0.03), 2),
    np.round(np.arange(0.78, 0.85, 0.01), 2),
    np.round(np.arange(0.85, 1.01, 0.03), 2),
]))
N_TRIALS = 6

eqs = '''
dv/dt = (v_rest - v + I_bg + I_ext + g_syn + xi*noise_amp*tau**0.5) / tau
    : volt (unless refractory)
dg_syn/dt = -g_syn / tau_syn : volt
I_bg : volt
I_ext : volt
'''


def ring_dist(a, b, n=N):
    d = np.abs(np.asarray(a) - np.asarray(b))
    return np.minimum(d, n - d)


def circular_centroid(spike_t, spike_i, t0, t1, n=N):
    mask = (spike_t >= t0) & (spike_t < t1)
    ids = spike_i[mask].astype(float)
    if ids.size == 0:
        return np.nan
    ang = 2 * np.pi * ids / n
    return (np.arctan2(np.mean(np.sin(ang)), np.mean(np.cos(ang)))
            / (2 * np.pi) * n) % n


def bump_centroids(sp_t, sp_i, win=10, step=5, t0=50, t1=300):
    t_wins = np.arange(t0, t1 - win, step)
    cents = [circular_centroid(sp_t, sp_i, t, t + win) for t in t_wins]
    return t_wins, np.array(cents)


def classify_trial(sp_t, sp_i, cue=CUE_CENTER, dist=DIST_CENTER, n=N):
    n_late = int(np.sum((sp_t > 250) & (sp_t < 300)))
    post_c = circular_centroid(sp_t, sp_i, 265, 295)
    if n_late < 5 or np.isnan(post_c):
        return 'collapsed', np.nan, n_late
    d_cue = ring_dist(post_c, cue, n)
    d_dist = ring_dist(post_c, dist, n)
    offset = post_c - cue
    if d_dist < d_cue:
        return 'relocated', offset, n_late
    else:
        return 'stable', offset, n_late


def run_condition(da, rng_seed, dist_amp=DIST_AMP):
    start_scope()
    seed(rng_seed)
    np.random.seed(rng_seed)

    G = NeuronGroup(N, eqs,
                    threshold='v > v_thr',
                    reset='v = v_reset',
                    refractory=2 * ms,
                    method='euler')
    G.v = v_rest + np.random.uniform(-2, 0, N) * mV
    G.I_bg = 15 * mV

    S = Synapses(G, G, 'w : volt', on_pre='g_syn_post += w')
    S.connect()
    d_norm = ring_dist(np.array(S.i), np.array(S.j)) / N
    S.w = (da * J_e * np.exp(-0.5 * (d_norm / sig_e) ** 2) - J_i) * mV

    spikes = SpikeMonitor(G)

    run(50 * ms)

    r = ring_dist(np.arange(N), CUE_CENTER)
    G.I_ext = np.where(r <= CUE_HW, CUE_AMP, 0.0) * mV
    run(100 * ms)

    G.I_ext = 0 * mV
    run(80 * ms)

    if dist_amp > 0:
        r2 = ring_dist(np.arange(N), DIST_CENTER)
        G.I_ext = np.where(r2 <= CUE_HW, dist_amp, 0.0) * mV
        run(30 * ms)
    else:
        run(30 * ms)

    G.I_ext = 0 * mV
    run(40 * ms)

    return np.array(spikes.t / ms), np.array(spikes.i, dtype=float)


def print_table(results_dict, da_vals, label):
    print(f"\n{label}")
    print(f"{'DA':>6}  {'stable':>7}  {'reloc':>7}  {'collap':>7}  "
          f"{'mean_off':>9}  {'sd':>6}  {'n':>3}  {'avg_spk':>8}")
    print("-" * 72)
    for da in da_vals:
        entries = results_dict[da]
        counts = {'stable': 0, 'relocated': 0, 'collapsed': 0}
        offsets = []
        for cls, off, nl in entries:
            counts[cls] += 1
            if not np.isnan(off):
                offsets.append(off)
        n_valid = len(offsets)
        mean_off = np.mean(offsets) if offsets else float('nan')
        sd_off = np.std(offsets) if offsets else float('nan')
        print(f"{da:6.2f}  {counts['stable']:7d}  {counts['relocated']:7d}  "
              f"{counts['collapsed']:7d}  {mean_off:+9.1f}  {sd_off:6.1f}  "
              f"{n_valid:3d}  {np.mean([nl for _, _, nl in entries]):8.0f}")


def compute_metrics(results_dict, da_vals):
    means, sds, collapse_rates = [], [], []
    for da in da_vals:
        entries = results_dict[da]
        offs = [off for cls, off, nl in entries if cls != 'collapsed'
                and not np.isnan(off)]
        collapse_count = len([1 for cls, _, _ in entries if cls == 'collapsed'])
        means.append(np.mean(offs) if offs else np.nan)
        sds.append(np.std(offs) if offs else np.nan)
        collapse_rates.append(collapse_count / N_TRIALS * 100)
    return means, sds, collapse_rates


t0 = time.time()

conditions = {
    'with_distractor': {'dist_amp': DIST_AMP, 'results': {}, 'traces': {}},
    'no_distractor':   {'dist_amp': 0.0,      'results': {}, 'traces': {}},
}

total_sims = len(da_vals) * N_TRIALS * len(conditions)

trial_counter = 0
for cond_name, cond in conditions.items():
    for da in da_vals:
        cond['results'][da] = []
        for trial in range(N_TRIALS):
            seed_val = 1000 + trial_counter
            trial_counter += 1
            sp_t, sp_i = run_condition(da, seed_val, dist_amp=cond['dist_amp'])
            cls, offset, n_late = classify_trial(sp_t, sp_i)
            cond['results'][da].append((cls, offset, n_late))
            if trial == 0:
                cond['traces'][da] = (sp_t, sp_i)

elapsed = time.time() - t0

print_table(conditions['with_distractor']['results'], da_vals,
            "WITH DISTRACTOR")
print_table(conditions['no_distractor']['results'], da_vals,
            "WITHOUT DISTRACTOR (control)")
print(f"\nSame random seeds used for both conditions.")
print(f"Elapsed: {elapsed:.0f}s\n")


# fig 1: control comparison

m_with, s_with, cr_with = compute_metrics(
    conditions['with_distractor']['results'], da_vals)
m_ctrl, s_ctrl, cr_ctrl = compute_metrics(
    conditions['no_distractor']['results'], da_vals)

fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(13, 5),
                                   gridspec_kw={'width_ratios': [2, 1]})
fig1.patch.set_facecolor('#0d0d0d')

for ax in [ax1a, ax1b]:
    ax.set_facecolor('#0d0d0d')
    ax.tick_params(colors='#aaaaaa')
    for sp in ax.spines.values():
        sp.set_edgecolor('#333333')

ax1a.plot(da_vals, cr_with, 'o-', color='#e05e5e', lw=1.8, markersize=5,
          label=f'with distractor ({DIST_AMP} mV)')
ax1a.plot(da_vals, cr_ctrl, 's--', color='#888888', lw=1.5, markersize=4,
          label='no distractor (control)')
ax1a.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax1a.set_ylabel('collapse rate (%)', color='#bbbbbb')
ax1a.set_title('is the collapse caused by the distractor?',
               color='#eeeeee', fontsize=11)
ax1a.set_ylim(-5, 110)
ax1a.legend(fontsize=8, facecolor='#1a1a1a', labelcolor='#bbbbbb',
            edgecolor='#333333')

ax1b.errorbar(da_vals, m_with, yerr=s_with, fmt='o-', color='#e05e5e',
              ecolor='#888888', capsize=3, lw=1.5, markersize=4,
              label='with distractor')
ax1b.errorbar(da_vals, m_ctrl, yerr=s_ctrl, fmt='s--', color='#888888',
              ecolor='#555555', capsize=3, lw=1.2, markersize=3,
              label='no distractor')
ax1b.axhline(0, color='#4fc97e', lw=0.8, linestyle=':', alpha=0.5)
ax1b.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax1b.set_ylabel('signed centroid offset from cue', color='#bbbbbb')
ax1b.set_title('centroid offset (non-collapsed trials only)',
               color='#eeeeee', fontsize=11)
ax1b.legend(fontsize=8, facecolor='#1a1a1a', labelcolor='#bbbbbb',
            edgecolor='#333333')

fig1.text(0.5, 0.01,
          'if the two curves overlap, the distractor is not causing '
          'the collapse, it is intrinsic instability',
          ha='center', color='#666666', fontsize=8.5, style='italic')
plt.tight_layout(rect=[0, 0.04, 1, 1])
plt.savefig(os.path.join(OUT_DIR, 'control_comparison.png'), dpi=150,
            facecolor=fig1.get_facecolor())
plt.close(fig1)


# fig 2: threshold sweep

fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(12, 4.5),
                                   gridspec_kw={'width_ratios': [2, 1]})
fig2.patch.set_facecolor('#0d0d0d')

for ax in [ax2a, ax2b]:
    ax.set_facecolor('#0d0d0d')
    ax.tick_params(colors='#aaaaaa')
    for sp in ax.spines.values():
        sp.set_edgecolor('#333333')

ax2a.errorbar(da_vals, m_with, yerr=s_with, fmt='o-',
              color='#e05e5e', ecolor='#888888', capsize=3,
              lw=1.6, markersize=5)
ax2a.axhline(0, color='#4fc97e', lw=0.8, linestyle=':', alpha=0.5,
             label='cue location')
ax2a.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax2a.set_ylabel('signed centroid offset from cue', color='#bbbbbb')
ax2a.set_title(f'WM accuracy vs DA  (n={N_TRIALS} trials/point)',
               color='#eeeeee', fontsize=11)
ax2a.legend(fontsize=8, facecolor='#1a1a1a', labelcolor='#bbbbbb',
            edgecolor='#333333')

ax2b.bar(da_vals, cr_with, width=0.025, color='#e05e5e', alpha=0.7)
ax2b.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax2b.set_ylabel('collapse rate (%)', color='#bbbbbb')
ax2b.set_title('bump collapse frequency', color='#eeeeee', fontsize=11)
ax2b.set_ylim(0, 105)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'da_threshold_sweep.png'), dpi=150,
            facecolor=fig2.get_facecolor())
plt.close(fig2)


# fig 3: failure mode breakdown

fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.patch.set_facecolor('#0d0d0d')
ax3.set_facecolor('#0d0d0d')
ax3.tick_params(colors='#aaaaaa')
for sp in ax3.spines.values():
    sp.set_edgecolor('#333333')

res = conditions['with_distractor']['results']
stable_c = [len([1 for cls, _, _ in res[da] if cls == 'stable']) for da in da_vals]
reloc_c = [len([1 for cls, _, _ in res[da] if cls == 'relocated']) for da in da_vals]
coll_c = [len([1 for cls, _, _ in res[da] if cls == 'collapsed']) for da in da_vals]

x = np.arange(len(da_vals))
bar_w = 0.6

ax3.bar(x, stable_c, bar_w, label='stable', color='#4fc97e')
ax3.bar(x, reloc_c, bar_w, bottom=stable_c, label='relocated', color='#f5a623')
ax3.bar(x, coll_c, bar_w, bottom=[s + r for s, r in zip(stable_c, reloc_c)],
        label='collapsed', color='#e05e5e', alpha=0.7)

ax3.set_xticks(x)
ax3.set_xticklabels([f'{da:.2f}' for da in da_vals], rotation=45, fontsize=8)
ax3.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax3.set_ylabel(f'trial count (n={N_TRIALS})', color='#bbbbbb')
ax3.set_title('failure mode breakdown (with distractor)',
              color='#eeeeee', fontsize=11)
ax3.legend(fontsize=9, facecolor='#1a1a1a', labelcolor='#bbbbbb',
           edgecolor='#333333')
ax3.set_ylim(0, N_TRIALS + 1)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'failure_mode_breakdown.png'), dpi=150,
            facecolor=fig3.get_facecolor())
plt.close(fig3)


# fig 4: heatmaps + centroid traces

show_da = [da_vals[-1], da_vals[len(da_vals) // 2], da_vals[0]]
show_labels = ['high DA', 'moderate DA', 'low DA']
show_colors = ['#4fc97e', '#f5a623', '#e05e5e']

T_TOTAL, BIN_MS = 300, 5
N_BINS = T_TOTAL // BIN_MS

fig4 = plt.figure(figsize=(16, 11))
fig4.patch.set_facecolor('#0d0d0d')
gs_top = gridspec.GridSpec(1, 3, figure=fig4, top=0.88, bottom=0.55,
                           wspace=0.3)
gs_bot = gridspec.GridSpec(1, 3, figure=fig4, top=0.47, bottom=0.09,
                           wspace=0.3)


def style_ax(ax):
    ax.set_facecolor('#0d0d0d')
    ax.tick_params(colors='#aaaaaa', labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor('#2a2a2a')


def epoch_lines(ax):
    for x, c in [(50, '#4fc97e'), (150, '#4c9be8'),
                  (230, '#f5a623'), (260, '#f5a623')]:
        ax.axvline(x, color=c, lw=0.9, linestyle='--', alpha=0.65)


for col, (da, label, color) in enumerate(
        zip(show_da, show_labels, show_colors)):
    sp_t, sp_i = conditions['with_distractor']['traces'][da]

    rate_map = np.zeros((N, N_BINS))
    for t_sp, i_sp in zip(sp_t, sp_i):
        b = int(t_sp / BIN_MS)
        if 0 <= b < N_BINS:
            rate_map[int(i_sp), b] += 1

    ax_h = fig4.add_subplot(gs_top[0, col])
    style_ax(ax_h)
    ax_h.imshow(rate_map, aspect='auto', origin='lower',
                extent=[0, T_TOTAL, 0, N],
                cmap='inferno', interpolation='bilinear',
                vmin=0, vmax=max(rate_map.max(), 1) * 0.9)
    epoch_lines(ax_h)
    ax_h.set_xlim(0, T_TOTAL)
    ax_h.set_ylim(0, N)

    cls, off, nl = classify_trial(sp_t, sp_i)
    ax_h.set_title(f'{label} (da={da:.2f}) [{cls}]',
                   color=color, fontsize=10, pad=5)
    ax_h.set_xlabel('time (ms)', color='#888888', fontsize=8)
    if col == 0:
        ax_h.set_ylabel('neuron', color='#888888', fontsize=8)
    else:
        ax_h.set_yticklabels([])

    t_w, cents = bump_centroids(sp_t, sp_i)
    valid = ~np.isnan(cents)

    ax_d = fig4.add_subplot(gs_bot[0, col])
    style_ax(ax_d)
    if valid.any():
        ax_d.plot(t_w[valid], cents[valid], color=color, lw=1.8, alpha=0.9)
        ax_d.scatter(t_w[valid], cents[valid], s=14, color=color,
                     zorder=3, edgecolors='none')
    ax_d.axhline(CUE_CENTER, color='#4fc97e', lw=1, linestyle=':',
                 alpha=0.8, label=f'cue ({CUE_CENTER})')
    ax_d.axhline(DIST_CENTER, color='#f5a623', lw=1, linestyle=':',
                 alpha=0.8, label=f'distractor ({DIST_CENTER})')
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

fig4.text(0.5, 0.99,
          'Dopamine-Modulated Working Memory - representative single trials',
          ha='center', va='top', color='#eeeeee', fontsize=12,
          fontweight='bold')
plt.savefig(os.path.join(OUT_DIR, 'ring_attractor_dopamine.png'), dpi=150,
            bbox_inches='tight', facecolor=fig4.get_facecolor())
plt.close(fig4)


# fig 5: parameter sensitivity

SIG_E_TEST = [0.04, 0.05, 0.06]
SIG_E_TRIALS = 6
DA_SUBSET = np.round(np.arange(0.72, 1.01, 0.04), 2)

sens_means = {sv: [] for sv in SIG_E_TEST}
sens_stds = {sv: [] for sv in SIG_E_TEST}
sens_n = {sv: [] for sv in SIG_E_TEST}

for sig_val in SIG_E_TEST:
    trial_ct = 0
    for da in DA_SUBSET:
        offsets_for_da = []
        n_collapsed = 0
        for trial in range(SIG_E_TRIALS):
            seed_val = 2000 + trial_ct
            trial_ct += 1

            start_scope()
            seed(seed_val)
            np.random.seed(seed_val)

            G = NeuronGroup(N, eqs,
                            threshold='v > v_thr',
                            reset='v = v_reset',
                            refractory=2 * ms,
                            method='euler')
            G.v = v_rest + np.random.uniform(-2, 0, N) * mV
            G.I_bg = 15 * mV

            S = Synapses(G, G, 'w : volt', on_pre='g_syn_post += w')
            S.connect()
            d_norm = ring_dist(np.array(S.i), np.array(S.j)) / N
            S.w = (da * J_e * np.exp(-0.5 * (d_norm / sig_val) ** 2)
                   - J_i) * mV

            sp = SpikeMonitor(G)

            run(50 * ms)
            r = ring_dist(np.arange(N), CUE_CENTER)
            G.I_ext = np.where(r <= CUE_HW, CUE_AMP, 0.0) * mV
            run(100 * ms)
            G.I_ext = 0 * mV
            run(80 * ms)
            r2 = ring_dist(np.arange(N), DIST_CENTER)
            G.I_ext = np.where(r2 <= CUE_HW, DIST_AMP, 0.0) * mV
            run(30 * ms)
            G.I_ext = 0 * mV
            run(40 * ms)

            sp_t = np.array(sp.t / ms)
            sp_i = np.array(sp.i, dtype=float)
            cls, off, nl = classify_trial(sp_t, sp_i)
            if cls == 'collapsed' or np.isnan(off):
                n_collapsed += 1
            else:
                offsets_for_da.append(off)

        n_survived = SIG_E_TRIALS - n_collapsed
        sens_n[sig_val].append(n_survived)
        if n_survived > 0:
            sens_means[sig_val].append(np.mean(offsets_for_da))
            sens_stds[sig_val].append(np.std(offsets_for_da))
        else:
            sens_means[sig_val].append(np.nan)
            sens_stds[sig_val].append(np.nan)

fig5, ax5 = plt.subplots(figsize=(8, 4.5))
fig5.patch.set_facecolor('#0d0d0d')
ax5.set_facecolor('#0d0d0d')
ax5.tick_params(colors='#aaaaaa')
for sp in ax5.spines.values():
    sp.set_edgecolor('#333333')

sig_colors = ['#e05e5e', '#f5a623', '#4fc97e']
for sig_val, color in zip(SIG_E_TEST, sig_colors):
    means = np.array(sens_means[sig_val])
    stds = np.array(sens_stds[sig_val])
    ns = np.array(sens_n[sig_val])
    valid = ~np.isnan(means)
    if valid.any():
        ax5.errorbar(DA_SUBSET[valid], means[valid], yerr=stds[valid],
                     fmt='o-', color=color, ecolor=color, elinewidth=1.2,
                     capsize=3, lw=1.6, markersize=5,
                     label=f'sig_e = {sig_val:.2f}')
    collapsed = ns == 0
    if collapsed.any():
        ax5.scatter(DA_SUBSET[collapsed], np.full(collapsed.sum(), -8),
                    marker='x', s=30, color=color, alpha=0.4, zorder=2)

ax5.axhline(0, color='#ffffff', lw=0.5, linestyle=':', alpha=0.3)
ax5.set_xlabel('dopamine gain (da)', color='#bbbbbb')
ax5.set_ylabel('signed centroid offset from cue', color='#bbbbbb')
ax5.set_title(f'parameter sensitivity: bump width  (n={SIG_E_TRIALS} trials/point)',
              color='#eeeeee', fontsize=11)
ax5.legend(fontsize=9, facecolor='#1a1a1a', labelcolor='#bbbbbb',
           edgecolor='#333333')
ax5.text(0.02, 0.02, 'x = all trials collapsed at this DA value',
         transform=ax5.transAxes, color='#666666', fontsize=7.5,
         style='italic', va='bottom')

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'parameter_sensitivity.png'), dpi=150,
            facecolor=fig5.get_facecolor())
plt.close(fig5)

total = (len(da_vals) * N_TRIALS * len(conditions)
        + len(SIG_E_TEST) * len(DA_SUBSET) * SIG_E_TRIALS)
print(f"Done: {total} sims in {time.time()-t0:.0f}s")
print(f"Figures saved to: {OUT_DIR}")