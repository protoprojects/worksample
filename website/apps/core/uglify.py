from compressor.filters import CompilerFilter


class UglifyFilter(CompilerFilter):
    command = "uglifyjs {infile} -m -c drop_console"
