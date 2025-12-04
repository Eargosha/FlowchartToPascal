from backend.constants import *


class Symbol:
    """Класс для представления символа (переменной или массива)."""

    def __init__(self, name, var_type='integer', is_array=False, array_size=(0, 100), declared=False, line=None,
                 pos=None):
        self.name = name
        self.base_type = var_type  # Базовый тип элементов (integer, real и т.д.)
        self.is_array = is_array  # Флаг: является ли символ массивом
        self.array_size = array_size  # Диапазон индексов (min, max)
        self.declared = declared
        self.line = line
        self.pos = pos

    @property
    def type(self):
        """Возвращает строковое представление типа для Pascal."""
        if self.is_array:
            low, high = self.array_size
            return f'array[{low}..{high}] of {self.base_type}'
        return self.base_type


class SymbolTable:
    """Класс для таблицы символов."""

    def __init__(self):
        self.symbols = {}

    def define(self, name, var_type='integer', is_array=False, array_size=None, declared=False, line=None, pos=None):
        """Определить (добавить или обновить) символ в таблицу."""
        if name not in self.symbols:
            self.symbols[name] = Symbol(
                name,
                var_type=var_type,
                is_array=is_array,
                array_size=array_size or (0, 100),  # Стандартный размер
                declared=declared,
                line=line,
                pos=pos
            )
        else:
            existing = self.symbols[name]

            # Если обновляем массив
            if is_array:
                existing.is_array = True
                if array_size:
                    existing.array_size = array_size

                # Обновляем базовый тип, если новый тип "шире" (real > integer)
                if var_type == 'real' and existing.base_type == 'integer':
                    existing.base_type = 'real'

            # Для обычных переменных
            elif var_type == 'real' and existing.base_type == 'integer':
                existing.base_type = 'real'

            if declared:
                existing.declared = True
            if line is not None and pos is not None and (existing.line is None or line < existing.line):
                existing.line = line
                existing.pos = pos

    def lookup(self, name):
        """Поиск символа по имени."""
        return self.symbols.get(name)

    def get_all_symbols(self):
        """Получить все символы."""
        return list(self.symbols.values())

    def print_table(self):
        """Вывести таблицу символов."""
        print("\n--- Таблица символов ---")
        for name, symbol in self.symbols.items():
            print(
                f"Имя: {name}, Тип: {symbol.type}, Объявлена: {symbol.declared}, Строка: {symbol.line}, Позиция: {symbol.pos}")
        print("-----------------------\n")

class SemanticAnalyzer:
    """Семантический анализатор AST PlantUML."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []

    def analyze(self, ast_root_node):
        """Запуск семантического анализа."""
        self.errors = []
        self.warnings = []
        self.symbol_table = SymbolTable()
        self._visit(ast_root_node)
        return self.symbol_table, self.errors, self.warnings

    def _visit(self, node):
        """Рекурсивный обход AST Node."""
        if not node:
            return

        self._process_node(node)

        if hasattr(node, 'children') and isinstance(node.children, list):
            for child in node.children:
                self._visit(child)

    def _process_node(self, node):
        """Обработка конкретного узла Node."""
        node_type = node.type
        node_value = node.value
        line = node.line
        pos = node.pos

        if node_type == "action_content" and node_value:
            self._analyze_action_content(node_value, line, pos)
        elif node_type == "condition_content" and node_value:
            self._analyze_condition_content(node_value, line, pos)

    def _analyze_action_content(self, content, line, pos):
        """Анализ содержимого действия."""
        content = content.strip()

        # Обработка ВВОДА с несколькими переменными
        if content.startswith("Ввод:"):
            vars_str = content[5:].strip()
            var_names = [v.strip() for v in re.split(r',\s*', vars_str) if v.strip()]

            for var_name in var_names:
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
                    self.symbol_table.define(var_name, var_type='integer', declared=True, line=line, pos=pos)
                else:
                    self.errors.append(f"Ошибка ({line},{pos}): Неверное имя переменной в Ввод: '{var_name}'")
            return

        # Обработка ВЫВОДА
        # if content.startswith("Вывод:"):
        #     output_content = content[6:].strip()
        #     # Если выводим строку в кавычках - это string
        #     if re.match(r'^["\'].*["\']$', output_content):
        #         return
        #
        #     # Если выводим переменную
        #     identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', output_content)
        #     for var_name in identifiers:
        #         symbol = self.symbol_table.lookup(var_name)
        #         if not symbol:
        #             self.warnings.append(
        #                 f"Предупреждение ({line},{pos}): Переменная '{var_name}' используется в 'Вывод:', но не была объявлена ранее.")
        #         self.symbol_table.define(var_name, line=line, pos=pos)
        #     return

        # Обработка ВЫВОДА
        if content.startswith("Вывод:"):
            output_content = content[6:].strip()

            # Если это пусто — ошибка
            if not output_content:
                self.warnings.append(f"Предупреждение ({line},{pos}): Пустой вывод")
                return

            # Разбиваем по запятым (как в Pascal)
            parts = [part.strip() for part in output_content.split(',')]
            processed_parts = []

            for part in parts:
                if not part:
                    continue

                # Проверяем: это строка в кавычках?
                if re.match(r'^["\'].*["\']$', part):
                    # Уже в кавычках — оставляем как есть (позже обработаем в генераторе)
                    processed_parts.append(part)
                # Это идентификатор (переменная)?
                elif re.fullmatch(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part):
                    # Это переменная — проверяем её
                    symbol = self.symbol_table.lookup(part)
                    if not symbol:
                        self.warnings.append(
                            f"Предупреждение ({line},{pos}): Переменная '{part}' используется в 'Вывод:', но не объявлена ранее."
                        )
                    self.symbol_table.define(part, line=line, pos=pos)
                    processed_parts.append(part)
                else:
                    # Всё остальное — это строка БЕЗ кавычек → добавляем кавычки
                    processed_parts.append(f'"{part}"')

            # Сохраняем обработанное содержимое в блоке (для генератора)
            # Но SemanticAnalyzer не хранит это — поэтому генератор должен повторить логику
            # Или можно передать через AST, но проще — обрабатывать в генераторе

            # Пока просто выходим — основная логика будет в генераторе
            return

        # Обработка ПРИСВАИВАНИЯ (включая массивы)
        # Паттерн: "arr[i] := значение" или "var := значение"
        array_assign_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\[\s*(.+?)\s*\]\s*(:?=)\s*(.+)$', content)
        simple_assign_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(:?=)\s*(.+)$', content)

        if array_assign_match:
            arr_name = array_assign_match.group(1)
            index_expr = array_assign_match.group(2).strip()
            value_expr = array_assign_match.group(4).strip()

            # Определяем тип значения
            value_type = self.infer_type(value_expr, self.symbol_table)

            # Добавляем/обновляем массив
            self.symbol_table.define(
                arr_name,
                var_type=value_type,
                is_array=True,
                declared=True,
                line=line,
                pos=pos
            )

            # Анализируем переменные в индексе (например, "i")
            index_vars = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', index_expr)
            for idx_var in index_vars:
                if idx_var.lower() in PASCAL_KEYWORDS:
                    continue
                self.symbol_table.define(idx_var, line=line, pos=pos)

            return

        # Обработка ПРИСВАИВАНИЯ (поддержка и := и =)
        assignment_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(:?=)\s*(.+)$', content)
        if assignment_match:
            var_name = assignment_match.group(1)
            expression = assignment_match.group(3).strip()

            # Выводим тип для переменной
            var_type = self.infer_type(expression, self.symbol_table)
            self.symbol_table.define(var_name, var_type=var_type, declared=True, line=line, pos=pos)

            # Проверяем переменные в правой части
            expr_vars = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expression)
            for used_var in expr_vars:
                if used_var == var_name:
                    continue
                symbol = self.symbol_table.lookup(used_var)
                if not symbol:
                    self.warnings.append(
                        f"Предупреждение ({line},{pos}): Переменная '{used_var}' используется в выражении, но не объявлена ранее.")
                self.symbol_table.define(used_var, line=line, pos=pos)
            return

        # Если дошли сюда — это не Ввод, не Вывод, и не присваивание
        self.errors.append(
            f"Ошибка ({line},{pos}): Недопустимое содержимое блока: '{content}'. "
            f"Разрешены только: 'Ввод: ...', 'Вывод: ...', или 'переменная := выражение'."
        )
        return

        # Общий случай: пропускаем ваще все как есть, но так не нада
        # identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content)
        # for var_name in identifiers:
        #     # Игнорируем ключевые слова Pascal
        #     if var_name.lower() in PASCAL_KEYWORDS:
        #         continue
        #     symbol = self.symbol_table.lookup(var_name)
        #     if not symbol:
        #         self.warnings.append(
        #             f"Предупреждение ({line},{pos}): Переменная '{var_name}' используется, но не объявлена ранее.")
        #     self.symbol_table.define(var_name, line=line, pos=pos)

    def _analyze_condition_content(self, content, line, pos):
        """Анализ содержимого условия с распознаванием FOR-циклов."""
        content = content.replace('!=', '<>')

        # Проверка на FOR-цикл
        for_match = FOR_LOOP_PATTERN.match(content)
        if for_match:
            counter_var = for_match.group(1)
            start_expr = for_match.group(2).strip()
            direction = for_match.group(3).lower()
            end_expr = for_match.group(4).strip()

            # Объявляем счётчик цикла
            self.symbol_table.define(counter_var, var_type='integer', declared=True, line=line, pos=pos)

            # Анализируем переменные в границах цикла
            for expr in [start_expr, end_expr]:
                vars_in_expr = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expr)
                for var in vars_in_expr:
                    if var.lower() not in PASCAL_KEYWORDS:
                        self.symbol_table.define(var, line=line, pos=pos)
            return

        # Обычное условие
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content)
        for var_name in identifiers:
            if var_name.lower() in PASCAL_KEYWORDS:
                continue
            symbol = self.symbol_table.lookup(var_name)
            if not symbol:
                self.warnings.append(
                    f"Предупреждение ({line},{pos}): Переменная '{var_name}' используется в условии, но не объявлена ранее.")
            self.symbol_table.define(var_name, declared=True, line=line, pos=pos)

    def infer_type(self, expression_str, symbol_table):
        """
        Вывод типа выражения.
        Приоритет: string > real > integer > boolean
        """
        expr = expression_str.strip()

        # Проверка на вызов функции abs(...)
        if expr.startswith("abs(") and expr.endswith(")"):
            inner = expr[4:-1].strip()
            return self.infer_type(inner, symbol_table)  # Тип аргумент

        # Проверка на обращение к массиву: arr[index]
        array_match = ARRAY_ACCESS_PATTERN.match(expr)
        if array_match:
            arr_name = array_match.group(1)
            symbol = symbol_table.lookup(arr_name)
            if symbol and symbol.is_array:
                return symbol.base_type  # Возвращаем тип элементов массива
            return 'integer'  # По умолчанию

        # Строковые литералы
        if re.match(r'^["\'].*["\']$', expr):
            return 'string'

        # Логические значения
        if expr.lower() in ['true', 'false']:
            return 'boolean'

        # Числовые литералы
        num_match = re.match(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$', expr)
        if num_match:
            return 'real' if ('.' in expr or 'e' in expr.lower()) else 'integer'

        # Переменные
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', expr):
            symbol = symbol_table.lookup(expr)
            return symbol.type if symbol else 'integer'

        # Деление всегда дает real
        if re.search(r'[^/]=/\s*[^/]', expr) or re.search(r'[^<>=]/[^=]', expr):
            tokens = re.split(r'([+\-*/()])', expr)
            for token in tokens:
                token = token.strip()
                if not token:
                    continue
                if token == '/':
                    return 'real'

        # Проверка операций с real
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[\d.]+|[+\-*/()]', expr)
        for token in tokens:
            if token in ['+', '-', '*', '/']:
                continue

            # Проверяем тип операндов
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
                symbol = symbol_table.lookup(token)
                if symbol and symbol.type == 'real':
                    return 'real'
            elif re.match(r'^[+-]?(\d+\.?\d*|\.\d+)$', token):
                if '.' in token:
                    return 'real'

        return 'integer'

    # В класс SemanticAnalyzer добавьте:
    def get_all_issues(self):
        """Возвращает все проблемы (ошибки и предупреждения) в едином формате"""
        issues = []

        # Обработка ошибок
        for error_msg in self.errors:
            match = re.match(r"Ошибка \((\d+),(\d+)\): (.+)", error_msg)
            if match:
                issues.append({
                    'type': 'error',
                    'line': int(match.group(1)),
                    'pos': int(match.group(2)),
                    'message': match.group(3),
                    'source': 'semantic'
                })

        # Обработка предупреждений
        for warn_msg in self.warnings:
            match = re.match(r"Предупреждение \((\d+),(\d+)\): (.+)", warn_msg)
            if match:
                issues.append({
                    'type': 'warning',
                    'line': int(match.group(1)),
                    'pos': int(match.group(2)),
                    'message': match.group(3),
                    'source': 'semantic'
                })

        return issues