# Security

Workboard is a local, single-user application, not an authenticated network service. Run it on a trusted machine and keep its HTTP listener on loopback. Do not expose it through tunnels, proxies or shared hosting. Local processes and privileged browser extensions are outside its isolation boundary.

Normal mode reads potentially private local chats, Git metadata and selected project documents. Filename exclusions and token-pattern redaction are not comprehensive secret detection. The screen-share curtain and project filters are not access controls. Use synthetic demo mode for public examples.

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/rtmedia/bluelux-workboard/security/advisories/new). Include the affected commit, platform, impact and a minimal synthetic reproduction. Do not include real credentials, customer records or conversation logs. Do not open a public issue containing exploitation details or private data. If the private form is unavailable, open an issue requesting a private contact without disclosing the vulnerability.

This early project maintains the current main branch; no older release support window or response-time guarantee is promised. Report first and coordinate disclosure with the maintainers.

## Security controls and review limits

Source access is read-only, document reads are bounded and reject symlink components, and Git scans disable filesystem-monitor helpers and hooks. Status scans fail closed when external Git filters apply to tracked files, including Git LFS helpers. Source strings are treated as data and escaped for display. HTTP routes are fixed and use local Host/Origin checks, no-store responses and a restrictive content security policy. Finder accepts only exact indexed workspace paths. Handoffs copy drafts; they do not send prompts or execute cleanup.

The November 2026 pre-publication review covered source/data flows, command execution, HTTP controls, document paths, browser rendering, dependencies, tracked files and reachable Git history. It added adversarial regression tests for repository-configured monitors and filters, document symlinks, oversized files and non-regular session sources. The local-only check command does not launch remote background work. There are no third-party runtime packages to audit. Python, Git, browsers, macOS and optional GitHub CLI still need their own security updates.

This review is not an independent penetration test or a guarantee that all vulnerabilities or secrets have been found. No external security scanner was installed or run. Resource exhaustion by a hostile same-user process and continuously mutated local files is not an isolation guarantee. Never run unreviewed repository code or commands suggested by untrusted project/chat content just because Workboard displays them.
