import re


class Node:
    """Узел дерева синтаксического разбора"""
    def __init__(self, node_type, value=None, line=0, pos=0):
        self.type = node_type      # Тип узла (if_statement, assignment, comparison и т.д.)
        self.value = value         # Значение (лексема, оператор, число)
        self.children = []         # Дочерние узлы
        self.line = line           # Номер строки в исходном коде
        self.pos = pos             # Позиция в строке

    def add_child(self, child):
        """Добавление дочернего узла"""
        if child is not None:
            self.children.append(child)

    def __str__(self):
        return self._to_string("", "", True)

    def _to_string(self, prefix, child_prefix, is_last):
        """
        Рекурсивное представление дерева в виде строки с визуальными связями
        :param prefix: префикс для текущей строки
        :param child_prefix: префикс для дочерних элементов
        :param is_last: является ли текущий узел последним среди своих братьев
        """
        # Строим строку для текущего узла
        result = prefix

        # Определяем символ для текущего узла в зависимости от того, последний ли он
        if is_last:
            result += "└── "
            new_prefix = child_prefix + "    "
        else:
            result += "├── "
            new_prefix = child_prefix + "│   "

        # Добавляем информацию об узле
        result += f"{self.type}"
        if self.value is not None:
            result += f": {self.value}"
        if self.line > 0:
            result += f" (line: {self.line}, pos: {self.pos})"
        result += "\n"

        # Обрабатываем дочерние узлы
        for i, child in enumerate(self.children):
            is_child_last = (i == len(self.children) - 1)
            result += child._to_string(child_prefix + ("    " if is_last else "│   "),
                                      child_prefix + ("    " if is_last else "│   "),
                                      is_child_last)

        return result


class PlantUMLSyntaxAnalyzer:
    """Синтаксический анализатор для PlantUML-кода, сгенерированного редактором."""

    def __init__(self, lexer):
        """
        Инициализация синтаксического анализатора.
        :param lexer: экземпляр PlantUMLLexer с уже выполненным лексическим анализом.
        """
        self.lexer = lexer
        self.lex_table = lexer.get_lex_table()
        self.position = 0  # Текущая позиция в таблице лексем
        self.errors = []   # Список ошибок синтаксического анализа
        self.root = None   # Корень дерева разбора
        self.error_recovery_mode = False

    def current_token(self):
        """Получение текущей лексемы без продвижения."""
        if self.position < len(self.lex_table):
            return self.lex_table[self.position]
        return None

    def next_token(self):
        """Получение следующей лексемы и продвижение указателя."""
        token = self.current_token()
        if token is not None:
            self.position += 1
        return token

    def match(self, token_class, token_value=None):
        """
        Проверка совпадения текущей лексемы с ожидаемой.
        :param token_class: ожидаемый класс лексемы
        :param token_value: ожидаемое значение лексемы (необязательно)
        :return: bool - совпадает ли лексема
        """
        token = self.current_token()
        if token is None:
            return False

        if token['class'] != token_class:
            return False

        if token_value is not None and token['value'] != token_value:
            return False

        return True

    def expect(self, token_class, token_value=None, message=None):
        """
        Ожидание определенной лексемы с точной фиксацией позиции при ошибке.
        :return: лексема или None при ошибке
        """
        token = self.current_token()

        # Обработка конца файла
        if token is None:
            error_msg = f"Ошибка (конец файла): " + \
                        (message or f"Ожидается лексема класса {token_class}")
            self.errors.append(error_msg)
            return None

        # Проверка по классу
        if token['class'] != token_class:
            error_msg = f"Ошибка ({token['line']},{token['pos']}): " + \
                        (message or f"Ожидается лексема класса {token_class}, получено {token['class']}")
            self.errors.append(error_msg)
            return None

        # Проверка по значению
        if token_value is not None and token['value'] != token_value:
            error_msg = f"Ошибка ({token['line']},{token['pos']}): " + \
                        (message or f"Ожидается значение {token_value}, получено {token['value']}")
            self.errors.append(error_msg)
            return None

        return self.next_token()

    def parse(self):
        """Запуск синтаксического анализа."""
        self.position = 0
        self.errors = []
        self.error_recovery_mode = False
        self.root = self.parse_program()

        if not self.errors:
            print("Синтаксический анализ PlantUML завершен успешно.")
            return True
        else:
            print(f"Синтаксический анализ PlantUML завершен с ошибками: {len(self.errors)}")
            for error in self.errors:
                print(error)
            return False

    def parse_program(self):
        """Разбор программы: @startuml start <statements> stop @enduml."""
        node = Node("program", line=1, pos=1)

        #
        startuml_token = self.expect(1, 1, "Ожидается '@startuml'")
        if startuml_token is None:
            return node
        startuml_node = Node("startuml_keyword", startuml_token['text'], line=startuml_token['line'], pos=startuml_token['pos'])
        node.add_child(startuml_node)

        # start
        start_token = self.expect(1, 2, "Ожидается 'start'")
        if start_token is None:
            return node
        start_node = Node("start_node", start_token['text'], line=start_token['line'], pos=start_token['pos'])
        node.add_child(start_node)

        # <statements>
        while not self.match(1, 3):  # Пока не встретим 'stop'
            if self.position >= len(self.lex_table):
                break

            if self.match(1):  # Если следующий токен - ключевое слово
                keyword_value = self.current_token()['value']
                if keyword_value in [3, 13]:  # 'stop' или '@enduml'
                    break

            stmt = self.parse_statement()
            if stmt:
                node.add_child(stmt)
            else:
                # Если разбор не удался, продвигаем позицию для избежания зацикливания
                if self.position < len(self.lex_table):
                    self.next_token()

        # stop
        stop_token = self.expect(1, 3, "Ожидается 'stop'")
        if stop_token is None:
            return node
        stop_node = Node("stop_node", stop_token['text'], line=stop_token['line'], pos=stop_token['pos'])
        node.add_child(stop_node)

        #
        enduml_token = self.expect(1, 13, "Ожидается '@enduml'")
        if enduml_token is None:
            return node
        enduml_node = Node("enduml_keyword", enduml_token['text'], line=enduml_token['line'], pos=enduml_token['pos'])
        node.add_child(enduml_node)

        return node

    def parse_statement(self):
        """Разбор оператора: action, if, while."""
        token = self.current_token()
        if token is None:
            return None

        # :действие;
        if self.match(2, 4):  # ':' - разделитель для начала действия
            return self.parse_action()

        # if
        elif self.match(1, 4):  # 'if'
            return self.parse_if_statement()

        # repeat
        elif self.match(1, 11):  # 'repeat'
            return self.parse_repeat_until_loop()

        # while
        elif self.match(1, 8):  # 'while'
            return self.parse_while_loop()

        else:
            # Для неожиданных токенов, которые не являются началом оператора
            # Проверяем, не является ли это завершением блока
            if self.match(1, 7):  # 'endif'
                return None
            if self.match(1, 10):  # 'endwhile'
                return None

            error_msg = f"Ошибка ({token['line']},{token['pos']}): " + \
                       f"Неожиданный токен '{token['text']}' типа {token['class']}."
            self.errors.append(error_msg)
            return None

    def parse_action(self):
        """Разбор действия: ':' <ACTION_CONTENT> ';'."""
        node = Node("action_node", line=self.current_token()['line'], pos=self.current_token()['pos'])

        # ':'
        colon_token = self.expect(2, 4, "Ожидается ':' для начала действия")
        if colon_token is None:
            return node

        # <ACTION_CONTENT>
        content_token = self.current_token()
        if content_token is None or content_token['class'] != 4:  # ACTION_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается содержимое действия после ':'"
            self.errors.append(error_msg)
            return node

        content_token = self.next_token()
        content_node = Node("action_content", content_token['text'], line=content_token['line'], pos=content_token['pos'])
        node.add_child(content_node)

        # ';'
        semicolon_token = self.expect(2, 3, "Ожидается ';' после содержимого действия")
        if semicolon_token is None:
            return node

        return node

    def parse_if_statement(self):
        """Разбор условного оператора: 'if' '(' <COND_CONTENT> ')' 'then' <BRANCH_LABEL> <statement>* [ 'else' <BRANCH_LABEL> <statement>* ] 'endif'."""
        token = self.current_token()
        node = Node("if_statement", line=token['line'], pos=token['pos'])

        # 'if'
        if_token = self.expect(1, 4, "Ожидается ключевое слово 'if'")
        if if_token is None:
            return node

        # '('
        open_paren_token = self.expect(2, 1, "Ожидается '(' после 'if'")
        if open_paren_token is None:
            return node

        # <COND_CONTENT>
        cond_token = self.current_token()
        if cond_token is None or cond_token['class'] != 5: # COND/BRANCH_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается условие в скобках после 'if'"
            self.errors.append(error_msg)
            return node
        cond_token = self.next_token()
        cond_node = Node("condition_content", cond_token['text'], line=cond_token['line'], pos=cond_token['pos'])
        node.add_child(cond_node)

        # ')'
        close_paren_token = self.expect(2, 2, "Ожидается ')' после условия")
        if close_paren_token is None:
            return node

        # 'then'
        then_token = self.expect(1, 5, "Ожидается ключевое слово 'then'")
        if then_token is None:
            return node

        # <BRANCH_LABEL> (да)
        # '('
        open_bracket = self.expect(2, 1, "Ожидается '(' перед ярлыком ветвления 'then'")
        if open_bracket is None:
            return node

        # Ярлык ветвления
        branch_label_token = self.current_token()
        if branch_label_token is None or branch_label_token['class'] != 5: # COND/BRANCH_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается ярлык ветвления после '('"
            self.errors.append(error_msg)
            return node
        branch_label_token = self.next_token()
        branch_label_node = Node("branch_label", branch_label_token['text'], line=branch_label_token['line'], pos=branch_label_token['pos'])
        node.add_child(branch_label_node)

        # ')'
        close_bracket = self.expect(2, 2, "Ожидается ')' после ярлыка ветвления 'then'")
        if close_bracket is None:
            return node

        # <statement>* (тело then) - собираем несколько операторов
        then_body_nodes = []
        # Продолжаем разбор, пока не встретим 'else' или 'endif'
        while not self.match(1, 6) and not self.match(1, 7): # Пока не 'else' (6) и не 'endif' (7)
            stmt = self.parse_statement()
            if stmt:
                then_body_nodes.append(stmt)
            else:
                # Если не удалось разобрать оператор, выходим из цикла
                break

        # Создаем узел для ветки 'then' и добавляем все операторы
        if then_body_nodes:
            then_branch_node = Node("then_branch")
            for stmt in then_body_nodes:
                then_branch_node.add_child(stmt)
            node.add_child(then_branch_node)

        # ['else' <BRANCH_LABEL> <statement>* ]
        if self.match(1, 6): # 'else'
            else_token = self.next_token()

            # <BRANCH_LABEL> (нет)
            # '('
            open_bracket_else = self.expect(2, 1, "Ожидается '(' перед ярлыком ветвления 'else'")
            if open_bracket_else is None:
                # Продолжаем разбор, чтобы не прерывать структуру
                pass

            # Ярлык ветвления
            else_branch_label_token = self.current_token()
            if else_branch_label_token is not None and else_branch_label_token['class'] == 5:
                else_branch_label_token = self.next_token()
                else_branch_label_node = Node("else_branch_label", else_branch_label_token['text'], line=else_branch_label_token['line'], pos=else_branch_label_token['pos'])
                node.add_child(else_branch_label_node)
            # else: error_msg = "Ожидается ярлык ветвления для 'else'"

            # ')'
            if self.match(2, 2): # ')'
                self.next_token()

            # <statement>* (тело else) - собираем несколько операторов
            else_body_nodes = []
            # Продолжаем разбор, пока не встретим 'endif'
            while not self.match(1, 7): # Пока не 'endif' (7)
                stmt = self.parse_statement()
                if stmt:
                    else_body_nodes.append(stmt)
                else:
                    # Если не удалось разобрать оператор, выходим из цикла
                    break

            # Создаем узел для ветки 'else' и добавляем все операторы
            if else_body_nodes:
                else_branch_node = Node("else_branch")
                for stmt in else_body_nodes:
                    else_branch_node.add_child(stmt)
                node.add_child(else_branch_node)

        # 'endif'
        endif_token = self.expect(1, 7, "Ожидается ключевое слово 'endif'")
        if endif_token is None:
            return node

        return node

    def parse_branch_label(self):
        """Разбор ярлыка ветвления вида (да), (нет) и т.д."""
        # '('
        open_bracket = self.expect(2, 1, "Ожидается '(' перед ярлыком ветвления")
        if open_bracket is None:
            return None

        # Ярлык ветвления
        branch_label_token = self.current_token()
        if branch_label_token is None or branch_label_token['class'] != 5: # COND/BRANCH_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается ярлык ветвления после '('"
            self.errors.append(error_msg)
            # Пробуем восстановиться и продолжить
            if self.match(2, 2): # ')'
                self.next_token()
            return None

        branch_label_token = self.next_token()
        branch_label_node = Node("branch_label", branch_label_token['text'], line=branch_label_token['line'], pos=branch_label_token['pos'])

        # ')'
        close_bracket = self.expect(2, 2, "Ожидается ')' после ярлыка ветвления")
        if close_bracket is None:
            return None

        return branch_label_node

    def parse_while_loop(self):
        """Разбор цикла while: 'while' '(' <COND_CONTENT> ')' 'is' <BRANCH_LABEL> <statement>* 'endwhile' <BRANCH_LABEL>."""
        token = self.current_token()
        node = Node("while_loop_node", line=token['line'], pos=token['pos'])

        # 'while'
        while_token = self.expect(1, 8, "Ожидается ключевое слово 'while'")
        if while_token is None:
            return node

        # '('
        open_paren_token = self.expect(2, 1, "Ожидается '(' после 'while'")
        if open_paren_token is None:
            return node

        # <COND_CONTENT>
        cond_token = self.current_token()
        if cond_token is None or cond_token['class'] != 5: # COND/BRANCH_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается условие в скобках после 'while'"
            self.errors.append(error_msg)
            return node
        cond_token = self.next_token()
        cond_node = Node("condition_content", cond_token['text'], line=cond_token['line'], pos=cond_token['pos'])
        node.add_child(cond_node)

        # ')'
        close_paren_token = self.expect(2, 2, "Ожидается ')' после условия")
        if close_paren_token is None:
            return node

        # 'is'
        is_token = self.expect(1, 9, "Ожидается ключевое слово 'is'")
        if is_token is None:
            return node

        # <BRANCH_LABEL> (да)
        branch_label_node = self.parse_branch_label()
        if branch_label_node:
            node.add_child(branch_label_node)
        else:
            return node

        # Тело цикла (может содержать несколько операторов)
        body_nodes = []
        while not self.match(1, 10):  # Пока не встретим 'endwhile'
            # Проверяем завершение программы
            if self.position >= len(self.lex_table) or self.match(1, 3) or self.match(1, 13):
                break

            stmt = self.parse_statement()
            if stmt:
                body_nodes.append(stmt)
            else:
                # Если разбор не удался, выходим из цикла
                break

        if body_nodes:
            body_node = Node("while_body")
            for stmt in body_nodes:
                body_node.add_child(stmt)
            node.add_child(body_node)

        # 'endwhile'
        endwhile_token = self.expect(1, 10, "Ожидается ключевое слово 'endwhile'")
        if endwhile_token is None:
            return node

        # <BRANCH_LABEL> (нет)
        end_branch_label_node = self.parse_branch_label()
        if end_branch_label_node:
            node.add_child(end_branch_label_node)
        # else: ошибку не добавляем, так как это не критично для структуры

        return node

    def parse_repeat_until_loop(self):
        """Разбор цикла repeat-until: 'repeat' <statement>* 'repeat while' '(' <COND_CONTENT> ')' 'is' <BRANCH_LABEL>."""
        token = self.current_token()
        node = Node("repeat_until_loop_node", line=token['line'], pos=token['pos'])

        # 'repeat' (первый токен в теле цикла)
        repeat_token = self.expect(1, 11, "Ожидается ключевое слово 'repeat'")
        if repeat_token is None:
            error_msg = f"Ошибка (конец файла): Ожидается ключевое слово 'repeat while' после тела цикла"
            self.errors.append(error_msg)
            return node

        # Тело цикла (может содержать несколько операторов)
        # Цикл продолжается до тех пор, пока не встретим 'repeat while' (KEYWORD 12) или 'stop'/'@enduml'
        body_nodes = []
        while True:
            # Проверяем, не начался ли 'repeat while' (ключевое слово 12) или завершение программы
            if self.match(1, 12):  # 'repeat while'
                break # Нашли 'repeat while', выходим из цикла разбора тела
            if self.match(1, 3) or self.match(1, 13):  # 'stop' или '@enduml'
                break # Конец программы

            stmt = self.parse_statement()
            if stmt:
                body_nodes.append(stmt)
            else:
                # Если разбор не удался, выходим из цикла
                break

        if body_nodes:
            body_node = Node("repeat_body")
            for stmt in body_nodes:
                body_node.add_child(stmt)
            node.add_child(body_node)

        # 'repeat while' (составной токен 12)
        # После выхода из цикла тела текущий токен должен быть 'repeat while'
        repeat_while_token = self.expect(1, 12, "Ожидается ключевое слово 'repeat while'")
        if repeat_while_token is None:
            # Если не нашли 'repeat while', значит цикл был неполным
            return node

        # '('
        open_paren_token = self.expect(2, 1, "Ожидается '(' после 'repeat while'")
        if open_paren_token is None:
            return node

        # <COND_CONTENT>
        cond_token = self.current_token()
        if cond_token is None or cond_token['class'] != 5: # COND/BRANCH_CONTENT
            error_msg = f"Ошибка ({self.current_token()['line'] if self.current_token() else 'EOF'}, {self.current_token()['pos'] if self.current_token() else 0}): " + \
                       "Ожидается условие в скобках после 'repeat while'"
            self.errors.append(error_msg)
            return node
        cond_token = self.next_token()
        cond_node = Node("condition_content", cond_token['text'], line=cond_token['line'], pos=cond_token['pos'])
        node.add_child(cond_node)

        # ')'
        close_paren_token = self.expect(2, 2, "Ожидается ')' после условия")
        if close_paren_token is None:
            return node

        # 'is'
        is_token = self.expect(1, 9, "Ожидается ключевое слово 'is'")
        if is_token is None:
            return node

        # <BRANCH_LABEL> (продолжить)
        branch_label_node = self.parse_branch_label()
        if branch_label_node:
            branch_label_node.type = "repeat_until_branch_label" # Уточняем тип узла ярлыка
            node.add_child(branch_label_node)
        # else: ошибку не добавляем, так как это не критично для структуры

        return node

    def print_syntax_tree(self):
        """Вывод дерева синтаксического разбора в улучшенном формате."""
        if self.root:
            print("\nДерево синтаксического разбора PlantUML:")
            print(str(self.root))
        else:
            print("Дерево разбора не построено (возможно, есть ошибки синтаксического анализа)")

    def get_syntax_tree(self):
        """Получение корня дерева синтаксического разбора."""
        return self.root

    # В класс PlantUMLSyntaxAnalyzer добавьте:
    def get_detailed_errors(self):
        """Преобразует ошибки в унифицированный формат с точными позициями"""
        detailed_errors = []
        pattern = re.compile(r"Ошибка\s*\(([^)]+)\):\s*(.+)")

        for error_msg in self.errors:
            match = pattern.match(error_msg)
            if not match:
                # Fallback для нестандартных сообщений
                detailed_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error_msg,
                    'source': 'parser'
                })
                continue

            position_info = match.group(1)
            message = match.group(2)

            # Обработка "конец файла"
            if position_info.lower() == "конец файла":
                detailed_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': message,
                    'source': 'parser'
                })
                continue

            # Обработка позиции "строка,столбец"
            pos_match = re.match(r"(\d+),(\d+)", position_info)
            if pos_match:
                line = int(pos_match.group(1))
                pos = int(pos_match.group(2))
                detailed_errors.append({
                    'type': 'error',
                    'line': line,
                    'pos': pos,
                    'message': message,
                    'source': 'parser'
                })
            else:
                # Fallback для неизвестного формата позиции
                detailed_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error_msg,
                    'source': 'parser'
                })

        return detailed_errors