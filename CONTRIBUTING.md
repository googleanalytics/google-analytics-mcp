# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution;
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google.com/conduct/).

## Code Style

This library conforms to [PEP 8](https://www.python.org/dev/peps/pep-0008/)
style guidelines and enforces an 80 character line width. It's recommended that
any contributor run the auto-formatter [`black`](https://github.com/psf/black).
To get started, first install `nox` and `black`:

```
pip install -e .[dev]
```

Then run the formatter on all Python files:

```
nox -s format
```

## Test changes

To test changes, modify the `command` for the `analytics-mcp` entry in your
`~/.gemini/settings.json` file so Gemini runs the server using your local
source files.

Replace `PATH_TO_REPO` in the following snippet with the path where you cloned
the repo:

```
      "command": "PATH_TO_REPO/.venv/bin/google-analytics-mcp",
```

