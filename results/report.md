# Rear Wing Optimization Report

_Generated: 2025-08-26 22:38:15_

## Best at 69.44 m/s (by L/D with sanity filters)

- **AoA**: 13.0°
- **Thickness**: 0.0025 m
- **Gurney**: 6 mm
- **L/D**: 4.354
- **Cd / Cl**: 0.102158 / 0.444820
- **Max disp**: 0.000247712 m
- **Max stress**: 2.014e+07 Pa

## Plots

- L/D vs AoA @ 69.44 m/s (all): `/case/results/plots/LD_vs_AoA_at_69p44ms.png`
- L/D vs AoA @ 69.44 m/s (Gurney=6 mm): `/case/results/plots/LD_vs_AoA_at_69p44ms_Gurney6mm.png`
- Displacement vs Speed (best): `/case/results/plots/Disp_vs_Speed_best.png`
- Stress vs Speed (best): `/case/results/plots/Stress_vs_Speed_best.png`

## Top designs @ 69.44 m/s (by L/D)

```
          timestamp  aoa_deg  thickness_m  speed_mps       Cd       Cl  L_over_D  max_disp_m  max_stress_Pa                                                         notes
2025-08-26 16:31:57     13.0       0.0025      69.44 0.102158 0.444820  4.354236    0.000248   2.014354e+07                              gurney=6mm | from simpleFoam.log
2025-08-26 16:33:09     14.0       0.0025      69.44 0.077087 0.335101  4.347044    0.000159   1.200852e+07                              gurney=6mm | from simpleFoam.log
2025-08-26 16:34:37     15.0       0.0025      69.44 0.073179 0.298833  4.083595    0.000077   7.565067e+06                              gurney=6mm | from simpleFoam.log
2025-08-25 15:13:33     12.0       0.0025      69.44 0.100768 0.385429  3.824915    0.000283   2.628106e+07 gurney=3mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-25 13:42:11     12.0       0.0025      69.44 0.100768 0.385429  3.824915    0.000283   2.628106e+07 gurney=3mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-25 13:31:18     12.0       0.0025      69.44 0.118345 0.442693  3.740699    0.000363   3.305046e+07 gurney=6mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-25 13:42:26     12.0       0.0025      69.44 0.118345 0.442693  3.740699    0.000363   3.305046e+07 gurney=6mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-25 15:13:48     12.0       0.0025      69.44 0.118345 0.442693  3.740699    0.000363   3.305046e+07 gurney=6mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-26 16:00:35     16.0       0.0025      69.44 0.092220 0.338787  3.673682    0.000197   1.604385e+07          gurney=6mm, stability numerics | from simpleFoam.log
2025-08-25 21:35:08     16.0       0.0025      69.44 0.092220 0.338787  3.673682    0.000197   1.604385e+07       gurney=6mm (AoA16,t2.5,stability) | from simpleFoam.log
2025-08-25 15:14:02     12.0       0.0025      69.44 0.128128 0.469931  3.667668    0.000404   3.629396e+07 gurney=9mm suction-side (XY,-Y) + TEref | from simpleFoam.log
2025-08-25 13:42:40     12.0       0.0025      69.44 0.128128 0.469931  3.667668    0.000404   3.629396e+07 gurney=9mm suction-side (XY,-Y) + TEref | from simpleFoam.log
```

## Worst designs @ 69.44 m/s (by L/D)

```
          timestamp  aoa_deg  thickness_m  speed_mps       Cd        Cl  L_over_D  max_disp_m  max_stress_Pa                                                      notes
2025-08-19 13:45:36      0.0       0.0030      69.44 0.038337  0.013155  0.343146    0.000192   4.699943e+06                                        from simpleFoam.log
2025-08-19 13:45:34      0.0       0.0025      69.44 0.038337  0.013155  0.343146    0.000276   5.812563e+06                                        from simpleFoam.log
2025-08-19 13:45:33      0.0       0.0020      69.44 0.038337  0.013155  0.343146    0.000430   7.477044e+06                                        from simpleFoam.log
2025-08-19 13:33:37      0.0       0.0020      69.44 0.038337  0.013155  0.343146    0.000430   7.477044e+06                                        from simpleFoam.log
2025-08-19 13:33:38      0.0       0.0025      69.44 0.038337  0.013155  0.343146    0.000276   5.812563e+06                                        from simpleFoam.log
2025-08-19 13:33:40      0.0       0.0030      69.44 0.038337  0.013155  0.343146    0.000192   4.699943e+06                                        from simpleFoam.log
2025-08-25 11:41:12     12.0       0.0025      69.44 0.075930 -0.000186 -0.002456    0.001249   2.856430e+07          baseline (refs+dirs locked) | from simpleFoam.log
2025-08-25 11:38:21     12.0       0.0025      69.44 0.075930 -0.000186 -0.002456    0.001249   2.856430e+07                  baseline (pitch-XZ) | from simpleFoam.log
2025-08-25 11:43:59     18.0       0.0025      69.44 0.145191 -0.000900 -0.006196    0.000068   3.752673e+06            baseline (pitch-XZ AoA18) | from simpleFoam.log
2025-08-25 10:52:59     12.0       0.0025      69.44 0.071802 -0.000826 -0.011502    0.000017   1.506616e+06 gurney=15mm,thick≈3mm (liftDir-down) | from simpleFoam.log
2025-08-25 11:38:29     12.0       0.0025      69.44 0.076331 -0.000897 -0.011746    0.000020   1.786164e+06     gurney=15mm,thick≈3mm (pitch-XZ) | from simpleFoam.log
2025-08-25 10:47:37     12.0       0.0025      69.44 0.071802 -0.170472 -2.374212    0.000017   1.506616e+06       gurney=15mm,thick≈3mm (meshed) | from simpleFoam.log
```