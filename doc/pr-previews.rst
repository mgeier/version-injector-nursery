Pull Request Previews
=====================

TODO: this section is only about GitHub,
other providers should be investigated as well.

At the time of writing,
building previews for pull requests is not directly supported by GitHub.
There are a few requests and discussions, though:

* https://github.com/orgs/community/discussions/7730
* https://github.com/actions/deploy-pages/issues/180
* https://github.com/actions/deploy-pages/issues/337

There is also this third-party project:

* https://github.com/rossjrw/pr-preview-action

  * This currently doesn't support PR previews from forks,
    see https://github.com/rossjrw/pr-preview-action/pull/6.

In the meantime, the GitHub workflow configuration at
https://github.com/mgeier/version-injector-nursery/tree/main/.github/workflows
shows an example how PR previews (including from forks) can be implemented.
