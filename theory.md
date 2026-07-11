# Theory

## Ring attractor basics

Neurons on a ring with Mexican-hat connectivity. Strong local excitation, weak global inhibition. A bump of activity persists without input, encoding a location.

Think of it as a ball in a bowl. Excitation deepens the bowl, inhibition keeps the bump from spreading. The bump is stable as long as the excitatory drive is strong enough. Take away the excitation and there's nothing holding the activity together - it just decays back to baseline. Too much excitation relative to inhibition and the bump doesn't stay narrow, it spreads out and eventually blankets the whole ring.

This is why "ring attractor" and not just "recurrent network" - the ring geometry means the network has a continuum of equally valid stable states, one bump position for every point on the ring, rather than just one or two fixed points. Wherever the bump forms, it stays there once the cue is gone, because nothing along the ring favors one position over another except history (where the cue happened to land).

## Neuron and synapse dynamics

Each neuron is a leaky integrate-and-fire (LIF) unit:

$$\tau \frac{dv}{dt} = v_{rest} - v + I_{bg} + I_{ext} + g_{syn} + \xi \sigma \sqrt{\tau}$$

with a spike-and-reset rule: once $v$ crosses $v_{thr}$, the neuron fires and $v$ is reset to $v_{reset}$.

Nothing exotic here - $\tau$ sets how fast the membrane potential relaxes back toward rest, $I_{bg}$ is a constant background drive keeping the network near threshold, $I_{ext}$ is whatever external stimulus is being delivered (cue or distractor), $g_{syn}$ is the recurrent input coming from other neurons on the ring, and the last term is noise (Brian2's built-in Wiener process, scaled by $\sigma$).

Synaptic input decays exponentially between spikes:

$$\tau_{syn} \frac{dg_{syn}}{dt} = -g_{syn}$$

and gets a jump of size $w_{ij}$ every time presynaptic neuron $j$ fires. This is a standard simplification - synapses aren't given their own rise time, just an instantaneous jump followed by exponential decay. Fine for this kind of model, where the point is bump dynamics, not fine synaptic kinetics.

## Dopamine as gain

D1 receptors scale recurrent excitation. In the model, that's a single multiplicative parameter `da` on the excitatory part of the weight kernel:

$$w_{ij} = da \cdot J_e \cdot \exp(-0.5 \cdot (d_{ij} / \sigma_e)^2) - J_i$$

$d_{ij}$ is the circular distance between neurons $i$ and $j$ (shortest path around the ring, not the straight-line index difference - a neuron at position 0 and a neuron at position 99 are one step apart, not 99). $J_e$ sets the peak excitatory weight between neighboring neurons, $\sigma_e$ controls how far that excitation reaches before falling off (narrower = a tighter bump), and $J_i$ is a flat inhibitory offset applied everywhere, which is what keeps the tails of the Gaussian from just adding up into runaway activity across the whole ring.

High da = deep bowl = bump resists perturbation.
Low da = shallow bowl = bump dies or gets captured.

## Reading out the bump position

Because the network lives on a ring, you can't just average neuron indices to find where the bump is sitting - a bump split evenly around position 0 (half the activity at index 98, half at index 1) would average out to roughly 50, which is nowhere near where the activity actually is. The fix is to treat each neuron's position as an angle and take a circular mean:

$$\theta_i = \frac{2\pi i}{N}, \qquad \text{centroid} = \frac{N}{2\pi} \cdot \text{atan2}\left(\langle \sin\theta_i \rangle, \langle \cos\theta_i \rangle\right)$$

This is the same circular-mean trick used for anything periodic - wind direction, time of day, phase of an oscillation. It correctly wraps around the boundary instead of getting fooled by it.

## What the sweep shows

16 DA values, 6 trials each, plus a no-distractor control with identical seeds.

Three outcomes:
1. **Stable**: bump survives, small perturbations only
2. **Relocated**: bump moves to distractor position (rare, only at boundary)
3. **Collapsed**: bump dies during the delay period

The transition is sharp: 33% stable at da=0.79, 100% stable at da=0.80. The no-distractor control shows identical collapse rates below 0.79, showing the collapse is intrinsic, not distractor-driven.

Why does the transition look sharp rather than gradual? Loosely, this is the same kind of behavior you'd expect from any system with a stability threshold - below a critical excitation level, the "bowl" from the ball-and-bowl picture above just isn't deep enough to hold a bump at all, so activity decays away regardless of noise. Above that level, the bowl is deep enough that ordinary trial-to-trial noise isn't enough to knock the bump out, so it survives reliably. Because that switch (bowl exists vs. bowl doesn't) is closer to a yes/no property of the network than a smoothly varying one, small changes in da right around the threshold can flip the outcome for most trials at once - hence the jump between da=0.79 and da=0.80 rather than a slow decline. This is a qualitative description of what's going on, not a formal bifurcation analysis - nothing here computes eigenvalues or does a proper stability analysis of the fixed points.

## Connection to neuroscience

- Schizophrenia and aging involve reduced D1 signalling in PFC
- Dual-state theory (Durstewitz & Seamans, 2008): low D1 = fragile, interference-prone state
- The steep transition here illustrates that: gradual D1 reduction produces abrupt WM collapse

## Limitations

- LIF neurons (no adaptation, bursting)
- Single gain parameter (real D1 affects multiple conductances)
- No plasticity
- All-to-all connectivity
- Tuned parameters (not experimental measurements)

## Refs: 
- Compte, A., Brunel, N., Goldman-Rakic, P. S., & Wang, X.-J. (2000). Synaptic mechanisms and network dynamics underlying spatial working memory in a cortical network model. Cerebral Cortex, 10(9), 910–923. https://doi.org/10.1093/cercor/10.9.910
- Wang, X.-J. (2001). Synaptic reverberation underlying mnemonic persistent activity. Trends in Neurosciences, 24(8), 455–463. https://doi.org/10.1016/S0166-2236(00)01868-3
- Durstewitz, D., & Seamans, J. K. (2008). The dual-state theory of prefrontal cortex dopamine function with relevance to catechol-O-methyltransferase genotypes and schizophrenia. Biological Psychiatry, 64(9), 739–749. https://doi.org/10.1016/j.biopsych.2008.05.015
