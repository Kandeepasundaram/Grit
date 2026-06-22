# PRD.md - Product Requirements Document
# GRIT - Git Profile Manager - Smart Session-Based Git Client

## 1. Executive Summary

### 1.1 Product Overview
Git Profile Manager (GPM) is a session-based desktop application that intelligently manages Git user profiles across multiple repositories. It eliminates the friction of manual profile switching by providing context-aware, just-in-time profile selection through a background daemon with system tray integration.

### 1.2 Problem Statement
Developers frequently work across multiple Git repositories with different identities (work, personal, client projects). Current solutions require manual configuration changes, are error-prone, and lack context awareness. This leads to:
- Commits with wrong author information
- Time wasted on manual profile switching
- Inconsistent signing keys
- Accidental exposure of work credentials in personal projects

### 1.3 Target Users
- **Primary:** Software developers using Git across multiple projects
- **Secondary:** DevOps engineers managing multiple client repositories
- **Tertiary:** Open-source contributors with separate maintainer identities

### 1.4 Success Metrics
- 95% reduction in wrong-profile commits
- 80% of users find profile switching "seamless"
- < 2 seconds average time to profile selection
- Zero system performance impact on Git operations

## 2. Product Scope

### 2.1 In Scope
- Background daemon monitoring Git operations
- Session-based profile management with TTL
- System tray integration with profile switching
- CLI interface for power users
- VS Code extension for IDE integration
- Profile CRUD operations
- Auto-detection based on repository paths
- GPG signing key management per profile
- SSH key association per profile

### 2.2 Out of Scope (Phase 1)
- Mobile applications
- Web-based interface
- Cloud sync of profiles
- Team/shared profiles
- CI/CD integration
- Git server-side hooks
- Multi-factor authentication

## 3. User Stories

### 3.1 Core Functionality
**US-001:** As a developer, I want the app to automatically detect my Git profile based on the repository path so I don't have to switch manually.

**US-002:** As a developer, I want a system tray icon showing my current profile so I can see my active identity at a glance.

**US-003:** As a developer, I want to be prompted to select a profile when committing to a new repository so I can set the right identity.

**US-004:** As a developer, I want the app to remember my profile choice for a repository so I don't have to select it every time.

**US-005:** As a developer, I want to switch profiles from the system tray with one click.

### 3.2 Profile Management
**US-006:** As a developer, I want to create named profiles with name, email, GPG key, and SSH key.

**US-007:** As a developer, I want to edit existing profiles.

**US-008:** As a developer, I want to delete profiles I no longer need.

**US-009:** As a developer, I want to set default profiles for specific path patterns (e.g., `~/work/*` → Work profile).

### 3.3 Advanced Features
**US-010:** As a developer, I want the app to warn me if I'm about to commit with the wrong profile.

**US-011:** As a developer, I want to temporarily override the profile for a single commit.

**US-012:** As a developer, I want to see my commit history grouped by profile.

**US-013:** As a developer, I want the app to auto-lock specific repositories to a profile.

## 4. Functional Requirements

### 4.1 Daemon Service
**FR-001:** The application MUST run as a background daemon on system startup.
**FR-002:** The daemon MUST monitor Git operations with < 100ms latency.
**FR-003:** The daemon MUST consume < 50MB RAM when idle.
**FR-004:** The daemon MUST handle multiple repositories simultaneously.
**FR-005:** The daemon MUST recover gracefully from crashes.

### 4.2 Session Management
**FR-006:** The system MUST maintain per-repository sessions with profile association.
**FR-007:** Sessions MUST expire after a configurable time (default: 8 hours).
**FR-008:** The system MUST store session data in a structured format (JSON).
**FR-009:** Sessions MUST survive system restarts.
**FR-010:** The system MUST support manual session invalidation.

### 4.3 Profile Management
**FR-011:** Users MUST be able to create, read, update, and delete profiles.
**FR-012:** Profiles MUST support: name, email, GPG signing key, SSH key.
**FR-013:** Profiles MUST support path-based auto-detection patterns.
**FR-014:** The system MUST support at least 10 profiles simultaneously.
**FR-015:** Profile data MUST be stored securely in user home directory.

### 4.4 User Interface
**FR-016:** The app MUST provide a system tray icon with current profile display.
**FR-017:** The app MUST show a profile selection popup when needed.
**FR-018:** The popup MUST display: repository name, current profile, available profiles.
**FR-019:** The popup MUST support keyboard navigation.
**FR-020:** The app MUST provide a CLI interface for power users.

### 4.5 IDE Integration
**FR-021:** The app MUST provide a VS Code extension for IDE integration.
**FR-022:** The extension MUST hook into VS Code's commit workflow.
**FR-023:** The extension MUST display current profile in VS Code status bar.
**FR-024:** The extension MUST allow profile switching from within VS Code.

### 4.6 Git Integration
**FR-025:** The app MUST apply profile settings to Git config before commit.
**FR-026:** The app MUST support both global and local Git config settings.
**FR-027:** The app MUST support GPG signing per profile.
**FR-028:** The app MUST support SSH key selection per profile.
**FR-029:** The app MUST maintain Git command performance (< 50ms overhead).

## 5. Non-Functional Requirements

### 5.1 Performance
- **NFR-001:** Daemon startup time < 3 seconds
- **NFR-002:** Profile switching time < 500ms
- **NFR-003:** Popup display time < 200ms
- **NFR-004:** No noticeable Git command latency (< 50ms)
- **NFR-005:** Memory usage < 100MB

### 5.2 Platform Support
- **NFR-006:** Support macOS (10.15+)
- **NFR-007:** Support Windows (10+)
- **NFR-008:** Support Linux (Ubuntu 20.04+, Fedora 34+)
- **NFR-009:** Support both Intel and Apple Silicon (macOS)

### 5.3 Security
- **NFR-010:** All sensitive data (GPG keys, SSH keys) stored locally only
- **NFR-011:** No telemetry or data collection without explicit consent
- **NFR-012:** Profiles encrypted at rest (optional)

### 5.4 Usability
- **NFR-013:** 90% of users can complete profile setup in < 2 minutes
- **NFR-014:** Error messages must be clear and actionable
- **NFR-015:** Keyboard shortcuts documented and consistent
- **NFR-016:** Onboarding tutorial for first-time users

### 5.5 Reliability
- **NFR-017:** 99.9% uptime for daemon service
- **NFR-018:** Automatic crash recovery with state preservation
- **NFR-019:** Graceful handling of Git operation failures
- **NFR-020:** Session data integrity guaranteed

## 6. User Interface Specifications

### 6.1 System Tray Menu

Profile Manager
──────────────
✓ Work    (john@company.com)
  Personal (john@gmail.com)
  ClientX  (john@clientx.com)
──────────────
📊 Current Session: Work
⏰ Expires in: 6h 23m
──────────────
⚙️ Switch Profile...
📝 Edit Profiles...
🔒 Lock Current Profile
──────────────
🔄 Auto-Detect: ON
🔔 Notifications: ON
──────────────
🚪 Quit

## 7. Data Flow Diagrams
### 7.1 Session Creation Flow

User commits → Git detects operation → Daemon intercepts
→ Check session cache → No session → Show popup
→ User selects profile → Save session → Apply to Git
→ Allow commit → Update session timestamp

### 7.2 Profile Detection Flow
Git operation → Daemon triggered → Get repository path
→ Check path patterns → Match profile → Apply profile
→ Verify with session cache → Update if needed
→ Allow Git operation to proceed

## 8. Constraints and Assumptions
### 8.1 Technical Constraints

+ Python 3.8+ required

+ Git 2.25+ required

+ No internet connection required

+ No external dependencies beyond Python ecosystem


### 8.2 Business Constraints
+ Open-source only (phase 1)

+ No paid features planned

+ Community-driven development

+ MIT or Apache 2.0 license

## 8.3 Assumptions
+ Users have Git installed

+ Users are comfortable with command line

+ Users have system tray support

+ Users have write access to their home directory

## 9. Compliance and Standards
+ CS-001: GDPR compliance for data privacy

+ CS-002: OpenSSH standard for SSH key management

+ CS-003: RFC 822 compliance for email handling

+ CS-004: Git configuration standards compliance