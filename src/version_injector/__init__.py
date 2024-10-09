__version__ = '0.0.0'


def inject_files(current_path, prepare_injection):
    for html_path in current_path.rglob('*.html'):
        injection = prepare_injection(html_path.relative_to(current_path))
        remainder = html_path.read_text()
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
            section, sep, remainder = remainder.partition('-below-->')
            if sep == '':
                # TODO: somehow continue?
                raise RuntimeError(
                    'error! malformed marker? missing opening marker?')
            chunks.append(section)
            chunks.append(sep)
            discard, sep, remainder = remainder.partition(
                f'<!--version-injector-injects-{section}-above-->')
            if sep == '':
                raise RuntimeError(
                    f'error/warning? no closing marker for {section!r}')
            chunks.append('\n')
            chunks.append(injection(section))
            chunks.append(sep)
        html_path.write_text(''.join(chunks))
