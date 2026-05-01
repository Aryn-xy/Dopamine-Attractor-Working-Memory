# Dopamine-Modulated Working Memory in a Ring Attractor Network

A spiking neural network simulation exploring how dopamine concentration affects
the stability of working memory under distractor interference.

Built with [Brian2](https://brian2.readthedocs.io/).

---

## Background

Ring attractor networks are a standard computational model for spatial working
memory - the kind used when you hold a location in mind during a delay period.
Neurons are arranged on a ring, connected by a Mexican-hat profile: strong local
excitation, weak global inhibition. A localised "bump" of activity can persist
without external input, encoding the remembered location.

The question here is: **what happens to that bump when a distractor appears, and
does dopamine level change the answer?**

D1 receptor activation in prefrontal cortex is known to scale recurrent
excitation. In this model, a single parameter `da` (∈ [0,1]) multiplies the
excitatory synaptic weights, mimicking D1-mediated gain modulation. This lets us
ask whether there is a critical DA threshold below which the memory trace becomes
vulnerable to interference.

---

## Model Equations

### Neuron dynamics (LIF with noise)

$$\tau \frac{dv}{dt} = v_{rest} - v + I_{bg} + I_{ext} + g_{syn} + \xi \sigma \sqrt{\tau}$$

Spike condition and reset:

$$v > v_{thr} \quad \Rightarrow \quad v \leftarrow v_{reset}$$

Each neuron integrates background drive, external input, recurrent synaptic current, and additive Gaussian white noise (amplitude $\sigma$, implemented as $\xi \sigma \sqrt{\tau}$). Parameters: $\tau = 15\text{ ms}$, $v_{rest} = v_{reset} = -70\text{ mV}$, $v_{thr} = -50\text{ mV}$.

---

### Synaptic dynamics (exponential decay)

$$\tau_{syn} \frac{dg_{syn}}{dt} = -g_{syn}$$

Incremented on each presynaptic spike:

$$g_{syn} \leftarrow g_{syn} + w_{ij}$$

Parameter: $\tau_{syn} = 5\text{ ms}$.

---

### Recurrent connectivity (Mexican-hat + dopamine gain)

$$w_{ij} = da \cdot J_e \cdot \exp\!\left(-\frac{1}{2}\left(\frac{d_{ij}}{\sigma_e}\right)^2\right) - J_i$$

where $d_{ij}$ is the circular distance between neurons $i$ and $j$ on the ring:

$$d_{ij} = \min(|i - j|,\; N - |i - j|)$$

and $da \in [0, 1]$ is the dopamine gain factor mimicking D1 receptor activation. Parameters: $J_e = 7.0\text{ mV}$, $J_i = 0.2\text{ mV}$, $\sigma_e = 0.05$.

Dopamine scales the recurrent excitatory gain $J_e^{eff} = da \cdot J_e$, shifting the network between stable and distractor-sensitive regimes:
- High $da$ → strong recurrent excitation → bump resists distractors
- Low $da$ → weak excitation → distractor can capture or destabilise the bump

---

### Bump centroid (circular mean readout)

$$\theta_i = \frac{2\pi i}{N}$$

$$\text{centroid} = \frac{N}{2\pi} \cdot \text{atan2}\!\left(\langle \sin \theta_i \rangle,\, \langle \cos \theta_i \rangle\right)$$

Population activity is decoded using a circular mean to correctly handle the periodic boundary of the ring. Reported centroid offsets in the Results table are relative to the cue location (neuron 50).

---

## Experimental Protocol

```
0 ms: baseline (50 ms, spontaneous) -> cue ON (100 ms at neuron 50) -> cue OFF (t = 150 ms) -> distractor (30 ms, half-amplitude at neuron 0) -> silence -> end (t = 260 ms)
```

Three DA conditions are run with identical noise seeds so the only variable is
dopamine level.

---

## Results

| DA level | Label | Late spikes (250–300 ms) | Final centroid offset |
|---|---|---:|---:|
| 1.00 | healthy | 352 | +3.7 neurons |
| 0.88 | fatigued | 174 | +3.7 neurons |
| 0.78 | depleted | 48 | +22.0 neurons |

At DA = 0.78, the late-period bump centroid (265-295 ms) is shifted by +22 neurons
relative to the cued location, indicating a large working-memory error after the
distractor period. At DA ≥ 0.88, the final centroid remains within ~4 neurons of
the cue, consistent with only noise-level perturbation.

These results indicate a sharp transition in attractor stability as a function of
dopamine level, consistent with a bifurcation between stable and distractor-sensitive
regimes - a critical DA value below which the memory trace becomes vulnerable to
interference.

---

## Key figure

![results](ring_attractor_dopamine.png)

Top row: population activity heatmaps across the three conditions. The bump
narrows and weakens with decreasing DA; at low DA, the distractor visibly pulls
activity away from the cued location during/after the distractor period (230–260 ms).

Bottom row: bump centroid tracked via circular mean of active neurons. High/moderate
DA centroids stay near neuron 50 throughout. Low DA centroid drifts to ~72 after
the distractor - a measurable working memory error.

---

## Possible extensions

- **DA-dependent synaptic plasticity** - instead of static weight scaling, let dopamine modulate STDP learning rates and test whether the network can self-organize a stable bump.
- **Multi-item working memory**- maintain two competing bumps with asymmetric DA; test whether the stronger attractor suppresses the weaker one or whether they can coexist.
- **Dopamine as an RL signal** - couple the ring attractor to a reward prediction error signal and test whether the network can learn which locations are worth remembering.

---

## Running it

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the simulation:
```bash
python ring_attractor_dopamine.py
```

Output: `ring_attractor_dopamine.png` + per-condition centroid summary printed
to stdout.

Main parameters are at the top of the file:

```python
J_e = 7.0      # peak excitatory weight (mV)
J_i = 0.2      # flat inhibitory offset (mV)
sig_e = 0.05     # Gaussian half-width (fraction of ring)
da_levels = [1.0, 0.88, 0.78]   # DA conditions to compare
```

---

## References

- Durstewitz, D., & Seamans, J. K. (2008). The dual-state theory of prefrontal cortex dopamine function with relevance to catechol-o-methyltransferase genotypes and schizophrenia. *Biological Psychiatry, 64*(9), 739–749. https://doi.org/10.1016/j.biopsych.2008.05.015
- Wang, X.-J. (2001). Synaptic reverberation underlying mnemonic persistent activity. *Trends in Neurosciences, 24*(8), 455–463. https://doi.org/10.1016/S0166-2236(00)01868-3
- Compte, A., Brunel, N., Goldman-Rakic, P. S., & Wang, X.-J. (2000). Synaptic mechanisms and network dynamics underlying spatial working memory in a cortical network model. *Cerebral Cortex, 10*(9), 910–923. https://doi.org/10.1093/cercor/10.9.910
