# XynaFaith Mobile Architecture

---

# Purpose

This document defines the architecture of the XynaFaith native mobile application.

The objective is to maximize reuse of the existing XynaFaith platform while delivering a high-quality native mobile experience for Android and iOS.

This document serves as the architectural reference for all future mobile development.

---

# High-Level Architecture

```
                    PostgreSQL
                         │
                         │
                    FastAPI API
                         │
          REST API + JWT Authentication
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Web Application             Mobile Application
        (ui-faith)                  (Capacitor)
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                 Android                                  iOS
```

---

# Backend

The backend remains unchanged.

Technology

- FastAPI
- PostgreSQL
- JWT Authentication

Responsibilities

- Authentication
- User management
- Sermon Studio
- Prayer Wall
- Community
- Pastor Network
- Search
- AI services
- Future XynAssist APIs

---

# Frontend

The existing **ui-faith** application remains the single source of truth.

Responsibilities

- User Interface
- Business Logic
- API Integration
- State Management

The frontend must never be duplicated.

---

# Mobile Layer

Capacitor provides the bridge between the web application and native device capabilities.

Responsibilities

- Native Navigation
- Camera
- Push Notifications
- Biometrics
- Secure Storage
- Native Sharing
- Deep Linking
- Offline Support

---

# Native Platforms

Android

Primary development platform.

Used for:

- Emulator
- Device testing
- Performance testing

iOS

Supported through Capacitor.

Final validation and release will be performed through GitHub Actions using macOS runners and the Apple Developer Program.

---

# Future Architecture

The architecture is designed to support future Xynasoft products.

Future products include:

- XynaLegal
- XynaSignal
- Additional Xynasoft platforms

The mobile architecture should remain reusable across products.

---

# XynAssist

XynAssist will integrate as a shared AI platform.

It will not replace XynaFaith.

Instead, it will provide AI-powered capabilities while allowing XynaFaith to remain the primary user experience.

---

# Guiding Principles

- One Backend
- One Frontend
- One Authentication System
- Maximum Code Reuse
- Native User Experience
- Clean Architecture
- Production Quality