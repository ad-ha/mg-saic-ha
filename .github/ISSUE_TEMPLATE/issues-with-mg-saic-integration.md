---
name: Issues with MG SAIC Integration
about: Create an issue report
title: "[ISSUE]"
labels: bug
assignees: ''

---

**Describe the issue**
A clear and concise description of what the bug is.

**Environment**
- Home Assistant version [e.g. 2024.11.1]
- MG/SAIC Integration version [e.g 0.4.8]
- Installation method [HACS, Manual]
- Did you check if there's a current or closed [Issue](https://github.com/ad-ha/mg-saic-ha/issues)? (You should): no
- Did you enable debug before and are ready to post logs as required? (see Logs section below): no

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Logs**
Add the following to `configuration.yaml` on your Home Assistant and restart your instant. 
```
logger:
  default: warning
  logs:
    custom_components.mg_saic: debug
```

See [HomeAssistant docs](https://www.home-assistant.io/integrations/logger) for more information.

**Additional context**
Add any other context about the problem here.
