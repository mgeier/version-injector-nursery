import importlib.metadata
from pathlib import Path

import tomlkit

__version__ = '0.0.0'


def handle_command():
    # TODO: possible actions:
    #       - new build has been created, dirname and category has to be given
    #         - if already in TOML: inject versions only into the new build
    #           (the given category is ignored)
    #         - if not yet in TOML: add version/variant, inject versions everywhere
    #       - manual trigger, inject versions everywhere

    # TODO: before each injection batch:
    #       - delete subdirectories that are not listed in TOML
    #       - delete temporary versions after given delay (based on git information?)
    #         "expire_in": "6 months and 4 days", "never"
    #         or after a given number is reached?

    # TODO: when parsing TOML:
    #       - check that all names are unique
    #       - if no versions are available: error
    #       - check if all the names are non-empty (truthy?)
    #       - check if all names to be listed do exist

    f = Path('version-injector.toml')
    # TODO: better exception message?
    # If file doesn't exist in current directory -> exception
    config = tomlkit.load(f.open())
    base_path = Path(config['base-path'])
    if not base_path.exists():
        raise RuntimeError(f'"base-path" not found: {base_path}')
    default = config.get('default', (config.get('versions') or [None])[0])
    if default:
        default_path = base_path / default
        if not default_path.exists():
            raise RuntimeError(f'default directory not found: {default_path}')
        # TODO: re-write the redirecting index page
    else:
        # TODO: delete the redirecting index page
        pass

    # TODO: check command, potentially iterate over directories
    # TODO: if necessary, add given version to the appropriate list
    inject('0.1.0', default, base_path, config)
    # TODO: if necessary, save TOML file (after everything was successful)


def inject(current, default, base_path, config):
    current_path = base_path / current
    versions = config.get('versions', [])
    for f in current_path.rglob('*.html'):
        remainder = f.read_text()
        chunks = []
        while remainder:
            prefix, sep, remainder = remainder.partition(
                '<!--version-injector-injects-')
            chunks.append(prefix)
            if sep == '':
                # no more markers found
                assert remainder == ''
                break
            chunks.append(sep)
            category, sep, remainder = remainder.partition('-below-->')
            if sep == '':
                # TODO: somehow continue?
                raise RuntimeError(
                    'error! malformed marker? missing opening marker?')
            chunks.append(category)
            chunks.append(sep)
            discard, sep, remainder = remainder.partition(
                f'<!--version-injector-injects-{category}-above-->')
            if sep == '':
                raise RuntimeError(
                    f'error/warning? no closing marker for {category!r}')
            chunks.append('\n')
            if category == 'VERSIONS':
                chunks.append('<li>generated content!</li>\n')
                chunks.append('<li>more generated content!</li>\n')
            elif category == 'WARNING':
                if default and current != default:
                    #if current in vanguard and vanguard_warning:
                    #    pass
                    #elif current in versions and versions_warning:
                    #    pass
                    #elif current in variants and variants_warning:
                    #    pass
                    #elif current in unlisted and unlisted_warning:
                    #    pass
                    #else:
                    #    # TODO: skip the following!
                    #    pass

                    relative_path = base_path / default / f.relative_to(current_path)
                    while not relative_path.exists():
                        relative_path = relative_path.parent
                    replacement = {
                        'name': default,
                        'url': '/' + relative_path.relative_to(base_path).as_posix(),
                    }
                    # TODO: use template to create warning

                    chunks.append('<p><b>warning!</b></p>\n')
                    chunks.append('<p><b>another warning!</b></p>\n')
            else:
                raise RuntimeError(f'Unknown category: {category!r}')
            chunks.append(sep)
        f.write_text(''.join(chunks))


if __name__ == '__main__':
    handle_command()
