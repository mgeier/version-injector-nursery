__version__ = '0.0.0'


def inject_files(docs_path, current, prepare_injection):
    # TODO: proper logging
    print('injecting into', current)
    current_path = docs_path / current
    for html_path in current_path.rglob('*.html'):
        inject_file(
            html_path, prepare_injection(
                current, html_path.relative_to(current_path)))


def inject_file(html_path, injection):
    remainder = html_path.read_text()
    chunks = []
    while remainder:
        left = '<!--version-injector-injects-'
        prefix, left, remainder = remainder.partition(left)
        chunks.append(prefix)
        if left == '':
            # no more markers found
            assert remainder == ''
            break
        chunks.append(left)
        right = '-below-->'
        section, right, remainder = remainder.partition(right)
        # If the marker is malformed, "section" might span multiple lines
        if right == '' or '\n' in section:
            marker = left + section.split('\n')[0]
            raise RuntimeError(f'malformed opening marker: {marker!r}')
        chunks.append(section)
        chunks.append(right)
        closer = f'<!--version-injector-injects-{section}-above-->'
        discard, closer, remainder = remainder.partition(closer)
        if closer == '':
            raise RuntimeError(f'no closing marker for {section!r}')
        chunks.append('\n')  # Any existing newlines were discarded
        chunks.append(injection(section))
        chunks.append(closer)
    html_path.write_text(''.join(chunks))
