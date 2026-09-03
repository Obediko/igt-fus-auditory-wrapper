# Attribution and third-party notice

This repository is a clean, hardware-agnostic wrapper. It does **not** bundle the Radboud/Donders FUS Driving System, IGT device drivers, NeuroFUS/TPO control code, transducer/generator configuration, or calibration/conversion files.

The masking design is conceptually informed by:

- Hira Musarrat and Benjamin Kop, *Auditory Mask Generator – NeuroFUS Edition*.
- Marwan Engels' public TUS code-sharing examples, including a simple pulse-related auditory mask approach.
- Published work on TUS auditory confounds and masking, including Braun et al. (2020), Liang et al. (2023), and ITRUSST guidance.

No NeuroFUS/TPO hardware-control implementation is included. The site-local FUS installation remains independently licensed and governed by its maintainers.

The previous Dortmund adaptation by Apochi and Axmacher is available separately and has its own third-party licensing obligations. This repository intentionally avoids vendoring those restricted upstream components.
