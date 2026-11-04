# Xynasoft Mobile Coding Standards

---

# Philosophy

Write code that is easy to read, maintain, and extend.

Code is written once but read many times.

---

# File Headers

Every file must begin with a descriptive header explaining:

- Purpose
- Responsibilities
- Author
- Last Updated

---

# Function Documentation

Every public function requires documentation.

Include:

- Purpose
- Parameters
- Returns
- Exceptions
- Notes

---

# Comments

Comments should explain **why** something is done.

Avoid comments that simply repeat the code.

Good:

"This cache avoids repeated API calls."

Bad:

"Increment variable."

---

# Naming

Use descriptive names.

Avoid abbreviations.

---

# Error Handling

Never silently ignore exceptions.

Always provide meaningful error messages.

---

# Logging

Log important application events.

Do not log sensitive user information.

---

# Security

Never store secrets in source code.

Never expose JWT tokens.

Use secure storage on mobile devices.

---

# Git Commits

Examples

feat(auth): add biometric login

fix(prayer): resolve loading issue

docs(mobile): update architecture

refactor(search): improve search performance

---

# Pull Requests

Every pull request should include:

- Summary
- Testing performed
- Screenshots (if UI changes)
- Documentation updates