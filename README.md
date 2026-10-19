# Embedded Skin Lesion Scanner

An embedded computer vision and real-time calibration scanner built for the Raspberry Pi 5 and Camera Module 3 (Sony IMX708) with a 7" touchscreen interface. Designed as a preprocessing pipeline for dermatological classification.

---

## Features

- **Real-time Color Constancy:** Implements an adaptive Gray World algorithm against an achromatic white reference aperture to eliminate environmental color casts.
- **Exposure Normalization (ETTR):** Linear luminance standardization targeting a fixed mean intensity of $180 / 255$ (~70% sensor headroom) to maximize SNR while avoiding specular clipping.
- **7" Touchscreen Interface:** Fullscreen UI with on-screen touch buttons for focus lock, capture/freeze, and application controls.
- **Automated Standardized Output:** Crops and exports region-of-interest (ROI) images at $224 \times 224$ pixels ready for deep learning inference.

---

## Hardware Stack

- **SBC:** Raspberry Pi 5 (8GB)
- **Sensor:** Raspberry Pi Camera Module 3 (Sony IMX708, PDAF autofocus)
- **Display:** Official Raspberry Pi 7" Touchscreen Display

---

## Getting Started

### Prerequisites

Ensure your Raspberry Pi OS has libcamera and Picamera2 installed:

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy
```

## Next Steps (Phase 2)

- [ ] Integrate MobileNet v2 inference directly into the freeze-screen state.
- [ ] Implement inference latency and thermal monitoring on the Raspberry Pi 5.
- [ ] Validate cross-dataset generalization using the ISIC skin lesion archive.
