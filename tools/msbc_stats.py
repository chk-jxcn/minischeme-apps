#!/usr/bin/env python3
"""Where the bytes of an app image go (docs/APP_DEVELOPMENT_GUIDE.md, 16.7).

    python tools/msbc_stats.py apps/medicine.msbc

Prints the bytecode, symbol names, function headers, string and number
constants of the MSBC part, the web page and metadata after it, the names
repeated most often and the string literals stored more than once.
"""
import collections
import struct
import sys

TAGS = ('fixnum', 'flonum', 'bool', 'string', 'symbol', 'nil', 'void', 'code', 'pair', 'vector', 'lstring', 'bigint',
        'symref')


class Stats:
    def __init__(self, data):
        if data[:4] != b'MSBC':
            sys.exit('not an MSBC image')
        self.data, self.pos = data, 8
        self.version = struct.unpack_from('<H', data, 4)[0]
        self.bytes = collections.Counter()
        self.symbols = collections.Counter()
        self.strings = collections.Counter()
        self.table = []
        self.functions = 0
        if self.version >= 2:          # the symbol table: each name once
            for _ in range(self.u16()):
                n = self.u16()
                self.table.append(self.data[self.pos:self.pos + n])
                self.pos += n
                self.bytes['symbol names'] += 2 + n
            self.bytes['symbol names'] += 2
        self.code()

    def u8(self):
        self.pos += 1
        return self.data[self.pos - 1]

    def u16(self):
        self.pos += 2
        return struct.unpack_from('<H', self.data, self.pos - 2)[0]

    def u32(self):
        self.pos += 4
        return struct.unpack_from('<I', self.data, self.pos - 4)[0]

    def value(self):
        tag = self.u8()
        name = TAGS[tag] if tag < len(TAGS) else '?'
        if name in ('fixnum', 'flonum'):
            self.pos += 8
            self.bytes['numbers'] += 9
        elif name == 'bool':
            self.pos += 1
            self.bytes['other constants'] += 2
        elif name in ('string', 'symbol', 'lstring'):
            n = self.u32() if name == 'lstring' else self.u16()
            text = self.data[self.pos:self.pos + n]
            self.pos += n
            kind = 'symbol names' if name == 'symbol' else 'strings'
            self.bytes[kind] += 1 + (4 if name == 'lstring' else 2) + n
            (self.symbols if name == 'symbol' else self.strings)[text] += 1
        elif name in ('nil', 'void'):
            self.bytes['other constants'] += 1
        elif name == 'code':
            self.bytes['function headers'] += 1
            self.code()
        elif name == 'pair':
            self.bytes['other constants'] += 1
            self.value()
            self.value()
        elif name == 'vector':
            self.bytes['other constants'] += 3
            for _ in range(self.u16()):
                self.value()
        elif name == 'symref':     # the index as a LEB128 varint
            start = self.pos
            self.symbols[self.table[self.varint()]] += 1
            self.bytes['symbol references'] += 1 + self.pos - start
        elif name == 'bigint':
            self.pos += 1
            n = self.u16()
            self.pos += 4 * n
            self.bytes['numbers'] += 4 + 4 * n
        else:
            sys.exit(f'unknown constant tag {tag} at byte {self.pos - 1}')

    def varint(self):
        v, shift = 0, 0
        while True:
            b = self.u8()
            v |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                return v

    def code(self):
        start = self.pos
        if self.version >= 2:            # varints: length, params, stack, flags byte, constants
            code_len = self.varint()
            self.varint()
            self.varint()
            self.u8()
            nconst = self.varint()
        else:
            code_len, _params, _stack, _variadic, _inner, nconst = struct.unpack_from('<IHHBBH', self.data, self.pos)
            self.pos += 12
        self.functions += 1
        self.bytes['function headers'] += self.pos - start
        self.bytes['bytecode'] += code_len
        self.pos += code_len
        for _ in range(nconst):
            self.value()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = open(sys.argv[1], 'rb').read()
    st = Stats(data)
    msbc = st.pos
    print(f'{sys.argv[1]}: {len(data)} B = bytecode image {msbc} B (MSBC version {st.version}) '
          f'+ web page and metadata {len(data) - msbc} B')
    for kind, n in st.bytes.most_common():
        print(f'  {kind:17} {n:7} B  {100 * n / msbc:5.1f}%')
    if st.version >= 2:
        print(f'{st.functions} functions; {sum(st.symbols.values())} references (2-3 B each) to {len(st.table)} names '
              f'stored once ({st.bytes["symbol names"]} B)')
    else:
        once = sum(len(s) + 3 for s in st.symbols)
        print(f'{st.functions} functions; {sum(st.symbols.values())} references to {len(st.symbols)} names '
              f'(MSBC 1 stores the names in each function: {st.bytes["symbol names"]} B, {once} B with a table)')
    print('names used by the most functions:',
          ', '.join(f'{s.decode()} {n}' for s, n in st.symbols.most_common(10)))
    dup = [(s, n) for s, n in st.strings.most_common() if n > 1 and len(s) > 8]
    if dup:
        print('string literals stored more than once (a top-level define stores one):')
        for s, n in dup[:8]:
            print(f'  {n}x {len(s)} B  {s[:40].decode("utf-8", "replace")!r}')


if __name__ == '__main__':
    main()
