# Security Policy

## Supported versions

Security fixes are applied to the latest release line:

| Version | Supported |
| --- | --- |
| 0.3.x | Yes |
| < 0.3 | No |

`nexttext` requires Python 3.9 or newer. Please reproduce reports on a
supported Python version before submitting.

## Reporting a vulnerability

**Do not open a public issue or pull request for a security problem.**

Report vulnerabilities privately through GitHub's private vulnerability
reporting:

1. Go to <https://github.com/jpeckenpaugh/nexttext/security/advisories/new>.
2. Describe the issue, affected versions, and the impact.
3. Include a minimal reproduction and the Python version.
4. Remove secrets, credentials, and private text from logs and samples.

If private reporting is unavailable, contact the maintainers through a private
channel listed on the repository profile rather than disclosing details in a
public issue.

Please include:

- the affected version and Python version;
- the command or API call that triggers the issue;
- expected and observed behavior;
- any suggested fix or mitigation.

## What to expect

- We aim to acknowledge a report within 7 days.
- We will investigate privately and keep you informed of progress.
- We will credit reporters in the advisory unless you ask us not to.
- Please give us a reasonable window to release a fix before public disclosure.

## Scope

In scope:

- Arbitrary code execution, unsafe deserialization, or command injection
  through the library, CLI, lexicons, or integrations.
- Vulnerabilities in the packaging, build, release, or CI configuration.
- Path traversal, unintended file writes, or unsafe handling of untrusted
  input in the CLI and optional integrations.
- Dependency or supply-chain issues in the development tooling.
- Denial-of-service issues caused by pathological input under normal use.

Out of scope:

- Incorrect, biased, or awkward rewrites produced by the heuristic rules.
  These are quality issues, not security vulnerabilities; please use the bug
  template.
- The accuracy or fairness of the optional NLP backend or external services.
- Vulnerabilities in third-party services such as LanguageTool, PyPI, or
  GitHub.
- Reports that require access to a machine or account the attacker already
  controls.
- Social engineering or spam.

## Security limitations of the project

`nexttext` is a heuristic text-rewriting toolkit, not a safety, compliance, or
fairness product. Its output can still be wrong, biased, or semantically
changed. Do not rely on it as a security boundary or as the sole review step
for high-stakes, legal, medical, or production fairness decisions. The default
path performs deterministic text substitution with no network access and no
runtime dependencies.
