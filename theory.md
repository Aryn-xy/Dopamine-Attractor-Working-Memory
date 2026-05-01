# Theory Notes: Dopamine-Modulated Ring Attractor

---

## What is a bump, and why does it persist?

Neurons in this network are arranged on a ring. Each neuron has a "preferred
location" - its position on the ring. When you present a cue at position 50,
neurons near position 50 start firing. Through strong local excitation, they
recruit their neighbours. Through weak global inhibition, they suppress the rest
of the ring.

The result is a stable, localised packet of activity - a **bump** - sitting at
the cued location. When the cue disappears, the bump doesn't collapse. The
excitatory connections between nearby neurons keep driving each other, while
inhibition keeps the rest quiet. The network holds the location in mind without
any external input.

This is a **continuous attractor**: not a discrete memory of a few states, but
a continuous manifold of stable states, one for every position on the ring.

---

## Stability: excitation vs inhibition

Think of the attractor as a ball sitting in a bowl. The depth of the bowl is
set by the balance between recurrent excitation and global inhibition.

- **Excitation** pulls the bump inward - neurons fire, drive their neighbours,
  and the bump reinforces itself.
- **Inhibition** is the restoring force - it keeps the bump from spreading
  across the whole ring.

The bump is stable as long as the excitatory drive is strong enough to resist
perturbation. When a distractor appears at an opposing location, it tries to
pull the bump toward it. Whether it succeeds depends entirely on the depth of
the bowl - i.e., how strongly the original bump is self-sustaining.

---

## Dopamine as a gain on recurrent excitation

D1 receptor activation in prefrontal cortex scales up recurrent excitatory
synapses. In this model, that is captured by a single multiplicative factor:

$$J_e^{eff} = da \cdot J_e$$

High dopamine → deep attractor basin → the bump resists perturbation.  
Low dopamine → shallow basin → a distractor can pull the bump away from the
cued location, producing a measurable working memory error.

This is not just a metaphor. The connectivity kernel is literally scaled by
`da`:

$$w_{ij} = da \cdot J_e \cdot \exp\!\left(-\frac{1}{2}\left(\frac{d_{ij}}{\sigma_e}\right)^2\right) - J_i$$

Reducing `da` flattens the Gaussian peak while leaving the inhibitory floor
unchanged - the Mexican-hat profile becomes shallower on the excitatory side.

---

## Why the transition looks sharp

Between DA = 0.88 and DA = 0.78, late-period spike counts drop from 174 to 48
and centroid error jumps from ~4 to ~22 neurons. That is not a gradual
degradation - it looks like a threshold.

This is expected from nonlinear attractor dynamics. The network has (at least)
two qualitatively different regimes:

1. **Stable regime**: the bump is a strong enough attractor that noise and
   distractors only cause small perturbations. The system returns to the cued
   location after the distractor.

2. **Distractor-sensitive regime**: the attractor basin is too shallow. The
   distractor pushes the system over a tipping point and the bump either
   collapses or relocates to the distractor position.

The transition between these regimes is sharp because it corresponds to a
**bifurcation** - a qualitative change in the dynamics as a parameter crosses
a critical value. Near this threshold, small changes in `da` produce
disproportionately large changes in memory fidelity.

This is consistent with experimental observations that prefrontal dopamine
depletion produces abrupt, not gradual, working memory impairments.

---

## Connection to clinical relevance

The model is deliberately minimal, but the logic maps directly onto real
neuroscience:

- Schizophrenia and aging are associated with reduced D1 signalling in
  prefrontal cortex.
- The dual-state theory of prefrontal dopamine (Durstewitz & Seamans, 2008)
  predicts that reduced D1 tone shifts the network from a robust, noise-resistant
  state to a fragile, interference-prone state.
- The bifurcation seen here is a computational instantiation of that theory.

The model does not claim to explain schizophrenia. It does show that a
single-parameter perturbation to recurrent gain is sufficient to reproduce the
qualitative pattern of impaired distractor resistance at reduced dopamine levels.

---

*For model equations and parameter values, see the [README](README.md).*
