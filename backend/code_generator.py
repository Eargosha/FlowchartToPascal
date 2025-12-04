from backend.constants import *


class PascalCodeGenerator:
    """Генератор кода на Pascal из AST PlantUML."""

    def __init__(self, ast_root, symbol_table):
        self.ast_root = ast_root
        self.symbol_table = symbol_table
        self.code_lines = []
        self.errors = []
        self.indent_level = 0

    def generate(self):
        """Основной метод генерации кода."""
        try:
            self.code_lines = []
            self.indent_level = 0
            self.errors = []  # Сброс ошибок перед новой генерацией

            # Проверка корневого узла
            if not self.ast_root:
                self._record_error("Корневой узел AST отсутствует", source_line=-1)
                return "Ошибка генерации: отсутствует AST дерево."

            # Начало программы
            self._add_line("PROGRAM Generated;")
            self._add_line("")

            # Генерация раздела VAR
            self._generate_var_section()

            self._add_line("BEGIN")
            self.indent_level += 1

            # Обход AST
            program_node = self.ast_root
            if program_count := self._validate_program_node(program_node):
                for child in program_node.children:
                    if child.type not in ["startuml_keyword", "enduml_keyword"]:
                        self._visit(child)

            self.indent_level -= 1
            self._add_line("END.")

            # Если есть ошибки - возвращаем код с комментарием
            if self.errors:
                error_comment = "(* ОШИБКИ ГЕНЕРАЦИИ: " + "; ".join([e['message'] for e in self.errors]) + " *)"
                return error_comment + "\n" + "\n".join(self.code_lines)

            return "\n".join(self.code_lines)

        except Exception as e:
            self._record_error(f"Критическая ошибка генерации: {str(e)}", source_line=-1)
            return "(* КРИТИЧЕСКАЯ ОШИБКА *)\nОшибка генерации кода. Проверьте логику диаграммы."

    def get_errors(self):
        """Возвращает ошибки генерации"""
        return self.errors

    def _record_error(self, message, source_line=-1, source_pos=-1):
        """Унифицированная запись ошибки"""
        self.errors.append({
            'type': 'error',
            'line': source_line,
            'pos': source_pos,
            'message': message,
            'source': 'generator'
        })

    def _validate_program_node(self, node):
        """Проверка корректности корневого узла"""
        if not node:
            self._record_error("Корневой узел программы не найден")
            return False
        if node.type != "program":
            self._record_error(f"Ожидался узел типа 'program', получен '{node.type}'")
            return False
        return True

    def _add_line(self, line):
        """Добавление строки с текущим отступом."""
        try:
            indent = "    " * self.indent_level
            self.code_lines.append(f"{indent}{line}")
        except Exception as e:
            self._record_error(f"Ошибка формирования строки: {str(e)}")

    def _process_string_literals(self, expr):
        """Обрабатывает ВСЕ строковые литералы в выражении"""
        try:
            if not expr:
                return expr

            parts = re.split(r'(["\'].*?["\'])', expr)
            processed_parts = []

            for part in parts:
                if not part:
                    continue

                if re.match(r'^["\'].*["\']$', part):
                    inner = part[1:-1]
                    escaped_inner = inner.replace("'", "''")
                    processed_parts.append(f"'{escaped_inner}'")
                else:
                    processed_parts.append(part)

            return ''.join(processed_parts)
        except Exception as e:
            self._record_error(f"Ошибка обработки строковых литералов '{expr}': {str(e)}")
            return expr  # Возвращаем оригинал при ошибке

    def _generate_var_section(self):
        """Генерация раздела объявления переменных"""
        try:
            types_dict = {}
            for symbol in self.symbol_table.get_all_symbols():
                base_name = symbol.name

                # Проверка на None (защита от битых символов)
                if base_name is None:
                    self._record_error("Обнаружен символ без имени в таблице")
                    continue

                if base_name.lower() in PASCAL_KEYWORDS:
                    continue

                try:
                    pascal_type = symbol.type
                except AttributeError:
                    self._record_error(f"Символ '{base_name}' не имеет атрибута 'type'")
                    pascal_type = 'integer'

                if pascal_type not in types_dict:
                    types_dict[pascal_type] = set()
                types_dict[pascal_type].add(base_name)

            if types_dict:
                self._add_line("VAR")
                for var_type, names in sorted(types_dict.items()):
                    names_str = ', '.join(sorted(names))
                    self._add_line(f"{names_str}: {var_type};")
                self._add_line("")

        except Exception as e:
            self._record_error(f"Ошибка генерации раздела VAR: {str(e)}")

    def _visit(self, node):
        """Рекурсивный обход узлов AST."""
        if not node:
            return

        try:
            node_type = node.type
            current_line = getattr(node, 'line', -1)
            current_pos = getattr(node, 'pos', -1)

            if node_type == "program":
                for child in node.children:
                    self._visit(child)

            elif node_type == "start_node":
                pass

            elif node_type == "action_node":
                for child in node.children:
                    if child.type == "action_content":
                        self._generate_action(child.value, current_line, current_pos)

            elif node_type == "if_statement":
                self._generate_if(node, current_line, current_pos)

            elif node_type == "while_loop_node":
                self._generate_while(node, current_line, current_pos)

            elif node_type == "repeat_until_loop_node":
                self._generate_repeat_until(node, current_line, current_pos)

            elif node_type == "stop_node":
                pass

            elif node_type in ["then_branch", "else_branch", "while_body", "repeat_body"]:
                for child in node.children:
                    self._visit(child)

            elif node_type in ["startuml_keyword", "enduml_keyword", "condition_content", "branch_label"]:
                pass

            else:
                for child in getattr(node, 'children', []):
                    self._visit(child)

        except Exception as e:
            self._record_error(f"Ошибка обработки узла '{node_type}': {str(e)}",
                               source_line=getattr(node, 'line', -1))

    def _generate_action(self, content, line=-1, pos=-1):
        """Генерация кода для действия."""
        try:
            if not content:
                self._record_error("Пустое содержимое действия", source_line=line)
                return

            content = content.strip().replace('!=', '<>')

            if content.startswith("Ввод:"):
                vars_str = content[5:].strip()
                if not vars_str:
                    self._record_error("Пустой список переменных в Ввод:", source_line=line)
                    return

                var_names = [v.strip() for v in re.split(r',\s*', vars_str) if v.strip()]
                if var_names:
                    vars_list = ', '.join(var_names)
                    self._add_line(f"readln({vars_list});")
                return

            elif content.startswith("Вывод:"):
                output_content = content[6:].strip()
                if not output_content:
                    self._add_line("writeln();")
                    return

                # Разбиваем по запятым
                parts = [part.strip() for part in output_content.split(',')]
                processed_parts = []

                for part in parts:
                    if not part:
                        continue

                    # Строка в кавычках?
                    if re.match(r'^["\'].*["\']$', part):
                        # Убираем внешние кавычки и экранируем внутренние
                        inner = part[1:-1]
                        escaped = inner.replace("'", "''")
                        processed_parts.append(f"'{escaped}'")
                    # Переменная (идентификатор)?
                    elif re.fullmatch(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part):
                        processed_parts.append(part)
                    else:
                        # Обычный текст — оборачиваем в кавычки Pascal
                        escaped = part.replace("'", "''")
                        processed_parts.append(f"'{escaped}'")

                result = ", ".join(processed_parts)
                self._add_line(f"writeln({result});")
                return

            # Обработка ПРИСВАИВАНИЯ
            assignment_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(:?=)\s*(.+)$', content)
            if assignment_match:
                var_name = assignment_match.group(1)
                expression = assignment_match.group(3).strip()

                if re.match(r'^["\'].*["\']$', expression):
                    if expression.startswith('"') and expression.endswith('"'):
                        inner = expression[1:-1]
                    elif expression.startswith("'") and expression.endswith("'"):
                        inner = expression[1:-1]
                    else:
                        inner = expression

                    escaped_inner = inner.replace("'", "''")
                    pascal_string = f"'{escaped_inner}'"
                    self._add_line(f"{var_name} := {pascal_string};")
                else:
                    self._add_line(f"{var_name} := {expression};")
                return

            # Любые другие действия
            if content:
                self._add_line(f"{content};")

        except Exception as e:
            self._record_error(f"Ошибка генерации действия '{content}': {str(e)}",
                               source_line=line)

    def _generate_if(self, node, line=-1, pos=-1):
        """Генерация кода для условного оператора."""
        try:
            condition = ""
            then_branch = None
            else_branch = None

            for child in node.children:
                if child.type == "condition_content":
                    condition = child.value.replace('!=', '<>')
                elif child.type == "then_branch":
                    then_branch = child
                elif child.type == "else_branch":
                    else_branch = child

            if not condition:
                self._record_error("Отсутствует условие в IF-операторе", source_line=line)
                return

            self._add_line(f"IF ({condition}) THEN")
            self._add_line("BEGIN")
            self.indent_level += 1

            if then_branch:
                for stmt in then_branch.children:
                    self._visit(stmt)

            self.indent_level -= 1
            self._add_line("END")

            if else_branch:
                self._add_line("ELSE")
                self._add_line("BEGIN")
                self.indent_level += 1
                for stmt in else_branch.children:
                    self._visit(stmt)
                self.indent_level -= 1
                self._add_line("END")

            self._add_line(";")

        except Exception as e:
            self._record_error(f"Ошибка генерации IF-оператора: {str(e)}", source_line=line)

    def _generate_while(self, node, line=-1, pos=-1):
        """Генерация кода для цикла WHILE с распознаванием FOR-циклов."""
        try:
            condition = ""
            body = None

            for child in node.children:
                if child.type == "condition_content":
                    condition = child.value.replace('!=', '<>')
                elif child.type == "while_body":
                    body = child

            if not condition:
                self._record_error("Отсутствует условие в цикле", source_line=line)
                return
            if not body:
                self._record_error("Отсутствует тело цикла", source_line=line)
                return

            # РАСПОЗНАВАНИЕ FOR-ЦИКЛА
            for_match = FOR_LOOP_PATTERN.match(condition)
            if for_match:
                counter_var = for_match.group(1)
                start_value = self._process_string_literals(for_match.group(2).strip())
                direction = for_match.group(3).upper()
                end_value = self._process_string_literals(for_match.group(4).strip())

                self._add_line(f"FOR {counter_var} := {start_value} {direction} {end_value} DO")
                self._add_line("BEGIN")
                self.indent_level += 1

                for stmt in body.children:
                    self._visit(stmt)

                self.indent_level -= 1
                self._add_line("END;")
                return

            # ОБЫЧНЫЙ WHILE-ЦИКЛ
            self._add_line(f"WHILE ({condition}) DO")
            self._add_line("BEGIN")
            self.indent_level += 1

            for stmt in body.children:
                self._visit(stmt)

            self.indent_level -= 1
            self._add_line("END;")

        except Exception as e:
            self._record_error(f"Ошибка генерации цикла: {str(e)}", source_line=line)

    def _generate_repeat_until(self, node, line=-1, pos=-1):
        """Генерация кода для цикла REPEAT-UNTIL."""
        try:
            body = None
            condition = ""

            for child in node.children:
                if child.type == "repeat_body":
                    body = child
                elif child.type == "condition_content":
                    condition = child.value.replace('!=', '<>')

            if not body:
                self._record_error("Отсутствует тело REPEAT-UNTIL цикла", source_line=line)
                return
            if not condition:
                self._record_error("Отсутствует условие UNTIL", source_line=line)
                return

            self._add_line("REPEAT")
            self.indent_level += 1

            for stmt in body.children:
                self._visit(stmt)

            self.indent_level -= 1
            self._add_line(f"UNTIL ({condition});")

        except Exception as e:
            self._record_error(f"Ошибка генерации REPEAT-UNTIL цикла: {str(e)}", source_line=line)