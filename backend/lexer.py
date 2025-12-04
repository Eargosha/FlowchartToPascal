import re


class ChainHashMap:
    """Реализация таблицы идентификаторов с использованием метода цепочек."""

    def __init__(self, initial_size=10):
        """Инициализация хэш-таблицы."""
        self.size = initial_size
        self.buckets = [[] for _ in range(self.size)]

    def _hash(self, key):
        """Вычисляет хэш-индекс для ключа."""
        hash_val = 0
        for char in key:
            hash_val += ord(char)
        return hash_val % self.size

    def get(self, id_str):
        """Получает значение по идентификатору."""
        bucket_index = self._hash(id_str)
        bucket = self.buckets[bucket_index]

        for item in bucket:
            if item[0] == id_str:
                const_str = "const" if item[3] else "var"
                return item[1], item[2], item[3]
        return None

    def put(self, id_str, data, var_type="string", is_const=True):
        """Добавляет или обновляет идентификатор в таблице."""
        bucket_index = self._hash(id_str)
        bucket = self.buckets[bucket_index]

        # Проверяем, есть ли уже такой идентификатор в списке
        for i, item in enumerate(bucket):
            if item[0] == id_str:
                # Обновляем значение, тип и признак const/var
                bucket[i] = (id_str, data, var_type, is_const)
                return data

        # Если идентификатора нет, добавляем его
        bucket.insert(0, (id_str, data, var_type, is_const))
        return data

    def delete(self, id_str):
        """Удаляет идентификатор из таблицы."""
        bucket_index = self._hash(id_str)
        bucket = self.buckets[bucket_index]

        for i, item in enumerate(bucket):
            if item[0] == id_str:
                del bucket[i]
                return True
        return False

    def print_table(self):
        """Выводит содержимое таблицы в удобочитаемом формате."""
        print("\n--- Таблица идентификаторов ---")
        for i, bucket in enumerate(self.buckets):
            if len(bucket) > 0:
                print(f"Bucket {i}:")
                for item in bucket:
                    const_str = "const" if item[3] else "var"
                    print(f"  ID='{item[0]}', Value={item[1]}, Type={item[2]}, {const_str}")
            else:
                print(f"Bucket {i}: [Empty]")
        print("--------------------------------\n")


class PlantUMLLexer:
    def __init__(self, source_code):
        # Добавляем терминальный символ и убираем лишние пробелы в начале/конце
        self.source = source_code.rstrip() + '\0'
        self.position = 0
        self.buffer = ""
        self.current_char = self.source[self.position]

        # --- Таблицы ключевых слов, операторов, разделителей ---
        # Класс 1: Ключевые слова PlantUML
        self.keywords = {
            "@startuml": 1, "start": 2, "stop": 3, "if": 4, "then": 5, "else": 6, "endif": 7,
            "while": 8, "is": 9, "endwhile": 10, "repeat": 11, "repeatwhile": 12, "@enduml": 13
        }
        # Класс 2: Разделители и операторы
        self.delimiters_ops = {
            "(": 1, ")": 2, ";": 3, ":": 4
        }

        # --- Таблицы для идентификаторов и констант ---
        self.identifier_table = ChainHashMap()
        self.constant_table = ChainHashMap()

        # Внутренние словари для быстрого поиска
        self.identifiers = {}
        self.constants = {}

        # Счетчики
        self.id_counter = 1
        self.const_counter = 1

        # Таблица лексем
        self.lex_table = []

        # Обработка позиций
        self.line_num = 1
        self.char_pos = 0
        self.errors = []

    def advance(self):
        """Переход к следующему символу с отслеживанием позиции"""
        if self.current_char == '\n':
            self.line_num += 1
            self.char_pos = 0
        else:
            self.char_pos += 1

        self.position += 1
        if self.position >= len(self.source):
            self.current_char = '\0'
        else:
            self.current_char = self.source[self.position]

    def skip_whitespace(self):
        """Пропускает пробельные символы"""
        while self.current_char != '\0' and self.current_char.isspace():
            self.advance()

    def make_token(self, token_class, token_value, token_text, line=None, pos=None):
        """Формирование токена с указанием позиции"""
        line = line if line is not None else self.line_num
        pos = pos if pos is not None else self.char_pos - len(token_text) + 1

        self.lex_table.append({
            'class': token_class,
            'value': token_value,
            'text': token_text,
            'line': line,
            'pos': pos
        })

    def error(self, message):
        """Обработка ошибки с фиксацией точной позиции"""
        # Фиксируем позицию В МОМЕНТ возникновения ошибки
        error_line = self.line_num
        error_pos = self.char_pos

        error_msg = f"Ошибка ({error_line},{error_pos}): {message}"
        self.errors.append(error_msg)
        print(error_msg)

        # Пропускаем до следующего разделителя или конца строки
        while self.current_char != '\0' and not self.current_char.isspace() and self.current_char not in ['(', ')', ';',
                                                                                                          ':', '@']:
            self.advance()


    def scan(self):
        """Основной метод лексического анализа"""
        while self.current_char != '\0':
            # Пропускаем пробельные символы
            self.skip_whitespace()
            if self.current_char == '\0':
                break

                       # Обработка ключевых слов и идентификаторов
            if self.current_char.isalpha() or self.current_char == '@':
                start_pos = self.char_pos
                start_line = self.line_num

                # Собираем слово
                self.buffer = ""
                while self.current_char.isalnum() or self.current_char in ['@', '_', '-']:
                    self.buffer += self.current_char
                    self.advance()

                # Проверяем, является ли буфер началом составного слова и идёт ли после него пробел
                potential_word = self.buffer.strip()
                potential_word_lower = potential_word.lower()

                # Проверяем на составное ключевое слово "repeat while"
                if potential_word_lower == "repeat" and self.current_char.isspace():
                    # Сохраняем позицию и состояние до пробела
                    saved_pos = self.position
                    saved_char = self.current_char
                    saved_buffer = self.buffer # Хотя buffer уже "repeat"

                    # Пропускаем пробелы
                    self.skip_whitespace()
                    # Теперь проверяем, начинается ли следующее "слово" с 'while'
                    if self.current_char.isalpha():
                        temp_buffer = ""
                        temp_pos = self.position
                        temp_char = self.current_char
                        # Собираем следующее слово
                        while temp_char.isalnum() or temp_char in ['@', '_', '-']:
                            temp_buffer += temp_char
                            temp_pos += 1
                            if temp_pos < len(self.source):
                                temp_char = self.source[temp_pos]
                            else:
                                break

                        if temp_buffer.lower().strip() == "while":
                            # Это действительно "repeat while"
                            # Восстанавливаем позицию до начала "while"
                            self.position = saved_pos
                            self.current_char = self.source[self.position] if self.position < len(self.source) else '\0'
                            # Пропускаем пробелы до "while"
                            self.skip_whitespace()
                            # Прочитаем "while" и создадим составной токен
                            while_word = ""
                            while self.current_char.isalnum() or self.current_char in ['@', '_', '-']:
                                while_word += self.current_char
                                self.advance()

                            # Создаём один токен для "repeat while"
                            self.make_token(1, self.keywords["repeatwhile"], "repeat while", start_line, start_pos)
                            # Продолжаем анализ с новой позиции
                            continue

                # Если составное слово не подтвердилось, обрабатываем как обычное слово
                word = potential_word
                word_lower = word.lower()

                # Обычное ключевое слово или неизвестное слово
                if word_lower in self.keywords:
                    self.make_token(1, self.keywords[word_lower], word, start_line, start_pos)
                else:
                    self.error(f"Неизвестное ключевое слово: '{word}'")

            # Обработка действий (начинается с ":")
            elif self.current_char == ':':
                start_pos = self.char_pos
                start_line = self.line_num
                self.make_token(2, self.delimiters_ops[':'], ":", start_line, start_pos)
                self.advance()

                # Читаем содержимое действия до ';'
                start_content_pos = self.char_pos
                start_content_line = self.line_num
                self.buffer = ""
                while self.current_char != '\0' and self.current_char != ';':
                    self.buffer += self.current_char
                    self.advance()

                # # Читаем содержимое действия до ';'   ----- До правки для abs()
                # start_content_pos = self.char_pos
                # start_content_line = self.line_num
                # self.buffer = ""
                # while self.current_char != '\0' and self.current_char != ';':
                #     if self.current_char == '(':
                #         # Это начало условия внутри действия, обрабатываем отдельно
                #         break
                #     self.buffer += self.current_char
                #     self.advance()

                content = self.buffer.strip()
                if content:
                    # Добавляем содержимое действия в таблицу идентификаторов
                    if content not in self.identifiers:
                        id_num = self.id_counter
                        self.identifiers[content] = id_num
                        self.identifier_table.put(content, id_num)
                        self.id_counter += 1
                    else:
                        id_num = self.identifiers[content]

                    self.make_token(4, id_num, content, start_content_line, start_content_pos)

                if self.current_char == ';':
                    end_pos = self.char_pos
                    end_line = self.line_num
                    self.make_token(2, self.delimiters_ops[';'], ";", end_line, end_pos)
                    self.advance()
                else:
                    self.error("Ожидается ';' в конце действия")

            # Обработка условий (начинается с "(")
            elif self.current_char == '(':
                start_pos = self.char_pos
                start_line = self.line_num
                self.make_token(2, self.delimiters_ops['('], "(", start_line, start_pos)
                self.advance()

                # Читаем содержимое условия до ')'
                start_content_pos = self.char_pos
                start_content_line = self.line_num
                self.buffer = ""
                while self.current_char != '\0' and self.current_char != ')':
                    self.buffer += self.current_char
                    self.advance()

                content = self.buffer.strip()
                if content:
                    # Добавляем содержимое условия в таблицу констант
                    if content not in self.constants:
                        const_num = self.const_counter
                        self.constants[content] = const_num
                        self.constant_table.put(content, const_num)
                        self.const_counter += 1
                    else:
                        const_num = self.constants[content]

                    self.make_token(5, const_num, content, start_content_line, start_content_pos)

                if self.current_char == ')':
                    end_pos = self.char_pos
                    end_line = self.line_num
                    self.make_token(2, self.delimiters_ops[')'], ")", end_line, end_pos)
                    self.advance()
                else:
                    self.error("Ожидается ')' в конце условия")

            # Обработка разделителя ";"
            elif self.current_char == ';':
                start_pos = self.char_pos
                start_line = self.line_num
                self.make_token(2, self.delimiters_ops[';'], ";", start_line, start_pos)
                self.advance()

            # Неизвестный символ
            else:
                self.error(f"Неожиданный символ: '{self.current_char}'")
                self.advance()

        if not self.errors:
            print(f"Лексический анализ PlantUML завершен успешно. Обработано {len(self.lex_table)} лексем.")
        else:
            print(f"Лексический анализ PlantUML завершен с ошибками. Обработано {len(self.lex_table)} лексем.")
            for error in self.errors:
                print(error)

        return len(self.errors) == 0

    def print_tables(self):
        """Вывод таблиц идентификаторов и констант"""
        print("\n--- Таблица идентификаторов (содержимое действий) ---")
        print(f"{'ID':<15} {'Value':<10} {'Type':<15} {'Const/Var':<10}")
        print("-" * 50)
        for bucket_list in self.identifier_table.buckets:
            for item in bucket_list:
                const_str = "const" if item[3] else "var"
                print(f"{item[0]:<15} {item[1]:<10} {item[2]:<15} {const_str:<10}")

        print("\n--- Таблица констант (условия, ярлыки ветвлений) ---")
        print(f"{'ID':<15} {'Value':<10} {'Type':<15} {'Const/Var':<10}")
        print("-" * 50)
        for bucket_list in self.constant_table.buckets:
            for item in bucket_list:
                const_str = "const" if item[3] else "var"
                print(f"{item[0]:<15} {item[1]:<10} {item[2]:<15} {const_str:<10}")

    def print_lex_table(self):
        """Вывод таблицы лексем"""
        class_names = {
            1: "KEYWORD",
            2: "DELIM/OP",
            4: "ACTION_CONTENT",
            5: "COND/BRANCH_CONTENT"
        }

        print("\nТаблица лексем PlantUML:")
        print(f"{'Строка':<7} {'Позиция':<8} {'Класс':<20} {'Значение':<10} {'Текст':<30}")
        print("-" * 80)
        for token in self.lex_table:
            class_name = class_names.get(token['class'], f"Class {token['class']}")
            print(f"{token['line']:<7} {token['pos']:<8} {class_name:<20} {token['value']:<10} {repr(token['text']):<30}")

    def get_lex_table(self):
        """Получение таблицы лексем"""
        return self.lex_table

    def get_errors(self):
        """Получение списка ошибок"""
        return self.errors

    # В класс PlantUMLLexer добавьте:
    def get_detailed_errors(self):
        """Преобразует ошибки в унифицированный формат с точными позициями"""
        detailed_errors = []
        pattern = re.compile(r"Ошибка\s*\((\d+),(\d+)\):\s*(.+)")

        for error_msg in self.errors:
            match = pattern.match(error_msg)
            if match:
                line = int(match.group(1))
                pos = int(match.group(2))
                message = match.group(3)
                detailed_errors.append({
                    'type': 'error',
                    'line': line,
                    'pos': pos,
                    'message': message,
                    'source': 'lexer'
                })
            else:
                # Fallback для нестандартных сообщений
                detailed_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error_msg.replace("Ошибка: ", ""),
                    'source': 'lexer'
                })
        return detailed_errors