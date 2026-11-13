# Existing S4/S5 gradient verification
Base ec9764f03dcdca305b575b41514d0aa153d2aab7. Execute user specification inline without a new architecture or training.
1. Add research-only reverse-mode vector tape with named shared parameters; mirror S4/S5 and sum all uses before returning VJP.
2. Compare forward to unchanged Kotlin oracle, gradients to central differences of that oracle, K=1,3,8, fixed partial/full routes, empty/singleton/multiple memory.
3. Check source-state write→later-read composition with explicit identity k/v fixture; distinguish missing Wk/Wv from tested boundary.
4. Record deterministic inputs, coordinate/directional errors, invalid-input behavior, numeric counterexamples. Compile all core sources and run existing host harness.
5. Write bounded verdict and existing work log, commit and push separate branch with skip-ci.
No optimizer, training, Android effects, dependencies or changes to original specifications. Synthetic d128/m128 follows existing shape contract; it is not an architecture choice.
