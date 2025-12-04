import re

# Регулярное выражение для распознавания обращений к массивам: var[index]
ARRAY_ACCESS_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\[\s*(.+?)\s*\]$')

# Шаблон для FOR-цикла: "i := 1 to n" или "i := n downto 1"
FOR_LOOP_PATTERN = re.compile(
    r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:=\s*(.+?)\s+(to|downto)\s+(.+?)\s*$',
    re.IGNORECASE
)

# Глобальный список ключевых слов Pascal
PASCAL_KEYWORDS = {
    'and', 'abs', 'array', 'as', 'begin', 'case', 'class', 'const', 'constructor',
    'continue', 'destructor', 'div', 'do', 'downto', 'else', 'end', 'enum',
    'except', 'exports', 'file', 'finalization', 'finally', 'for', 'foreach',
    'forward', 'function', 'goto', 'if', 'implementation', 'in', 'inherited',
    'initialization', 'inline', 'interface', 'is', 'label', 'mod', 'new',
    'nil', 'not', 'object', 'of', 'operator', 'or', 'packed', 'procedure',
    'program', 'property', 'raise', 'record', 'repeat', 'sealed', 'set',
    'shl', 'shr', 'static', 'string', 'then', 'to', 'try', 'type',
    'unit', 'until', 'uses', 'var', 'while', 'with', 'xor',

    # булевы константы
    'true', 'false',

    # примитивные типы
    'integer', 'real', 'boolean', 'char',

    # модификаторы доступа
    'private', 'protected', 'public', 'internal',

    # управляемые конструкции
    'yield', 'break'
}
