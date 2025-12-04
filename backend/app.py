from flask import Flask, request, jsonify
from flask_cors import CORS

from backend.code_generator import PascalCodeGenerator
from backend.lexer import PlantUMLLexer
from backend.parser import PlantUMLSyntaxAnalyzer
from backend.sema import SemanticAnalyzer

app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы для фронтенда


@app.route('/generate-pascal', methods=['POST'])
def generate_pascal():
    """Эндпоинт для генерации Pascal кода из блок-схемы"""
    data = request.json

    if not data or 'plantuml' not in data:
        return jsonify({
            "success": False,
            "pascal_code": "",
            "errors": [{
                'type': 'error',
                'line': -1,
                'pos': -1,
                'message': "Не предоставлен код PlantUML",
                'source': 'request'
            }],
            "warnings": []
        }), 400

    print("[==+==] =====================Начало запроса==================== \n")

    plantuml_code = data.get('plantuml', '')
    all_errors = []
    all_warnings = []

    print("[==+==] Задача: \n")
    print(plantuml_code)

    # Шаг 1: Лексический анализ
    print("[==+==] Шаг 1: Лексический анализ: \n")
    lexer = PlantUMLLexer(plantuml_code)
    lexer_success = lexer.scan()

    if not lexer_success:
        # Получаем ошибки в унифицированном формате
        if hasattr(lexer, 'get_detailed_errors'):
            lexer_errors = lexer.get_detailed_errors()
            all_errors.extend(lexer_errors)
        elif hasattr(lexer, 'get_errors'):
            # Преобразуем старый формат в новый
            for error in lexer.get_errors():
                all_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error,
                    'source': 'lexer'
                })

        print("[==+==] Лексические ошибки: ", all_errors)
        return jsonify({
            "success": False,
            "pascal_code": "",
            "errors": all_errors,
            "warnings": all_warnings
        }), 400
    else:
        print("[==+==] Шаг 1 успешно: \n")

    # Шаг 2: Синтаксический анализ
    print("[==+==] Шаг 2: Синтаксический анализ: \n")
    parser = PlantUMLSyntaxAnalyzer(lexer)
    parse_success = parser.parse()

    if not parse_success:
        # Получаем ошибки в унифицированном формате
        if hasattr(parser, 'get_detailed_errors'):
            parser_errors = parser.get_detailed_errors()
            all_errors.extend(parser_errors)
        elif hasattr(parser, 'get_errors'):
            # Преобразуем старый формат в новый
            for error in parser.get_errors():
                all_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error,
                    'source': 'parser'
                })

        print("[==+==] Синтаксические ошибки: ", all_errors)
        return jsonify({
            "success": False,
            "pascal_code": "",
            "errors": all_errors,
            "warnings": all_warnings
        }), 400
    else:
        print("[==+==] Шаг 2 успешно: \n")

    # Шаг 3: Получаем AST
    ast_root = parser.get_syntax_tree()

    # ast красиво преобразуем в словарь для вывода на сайт
    def node_to_dict(node):
        """Рекурсивно преобразует AST-узел в словарь"""
        if not node:
            return None

        result = {
            'type': node.type,
            'value': getattr(node, 'value', None),
            'line': getattr(node, 'line', None),
            'pos': getattr(node, 'pos', None),
            'children': []
        }

        if hasattr(node, 'children') and node.children:
            for child in node.children:
                result['children'].append(node_to_dict(child))

        return result

    # В ответе API:
    ast_json = node_to_dict(ast_root) if ast_root else {}

    # Шаг 4: Семантический анализ
    print("[==+==] Шаг 3: Семантический анализ: \n")
    semantic_analyzer = SemanticAnalyzer()
    symbol_table, errors, warnings = semantic_analyzer.analyze(ast_root)

    if errors or warnings:
        # Получаем все проблемы (ошибки и предупреждения) в унифицированном формате
        if hasattr(semantic_analyzer, 'get_all_issues'):
            issues = semantic_analyzer.get_all_issues()
            for issue in issues:
                if issue['type'] == 'error':
                    all_errors.append(issue)
                elif issue['type'] == 'warning':
                    all_warnings.append(issue)
        else:
            # Преобразуем старый формат в новый
            for error in errors:
                all_errors.append({
                    'type': 'error',
                    'line': -1,
                    'pos': -1,
                    'message': error,
                    'source': 'semantic'
                })
            for warning in warnings:
                all_warnings.append({
                    'type': 'warning',
                    'line': -1,
                    'pos': -1,
                    'message': warning,
                    'source': 'semantic'
                })

    if all_errors:
        print("[==+==] Семантические ошибки: ", all_errors)
        print("[==+==] Предупреждения: ", all_warnings)
        return jsonify({
            "success": False,
            "pascal_code": "",
            "errors": all_errors,
            "warnings": all_warnings
        }), 400

    print("[==+==] Шаг 3 успешно: \n")

    # Шаг 5: Генерация кода Pascal
    print("[==+==] Шаг 4: Генерация кода Pascal: \n")
    try:
        code_generator = PascalCodeGenerator(ast_root, symbol_table)
        pascal_code = code_generator.generate()

        # Проверяем ошибки генератора
        if hasattr(code_generator, 'get_errors'):
            generator_errors = code_generator.get_errors()
            if generator_errors:
                for error in generator_errors:
                    if isinstance(error, dict):
                        all_errors.append(error)
                    else:
                        all_errors.append({
                            'type': 'error',
                            'line': -1,
                            'pos': -1,
                            'message': str(error),
                            'source': 'generator'
                        })

        print(pascal_code)
    except Exception as e:
        print(f"[==+==] Ошибка при генерации кода: {e}")
        # Возвращаем код с ошибкой для отладки
        pascal_code = f"""PROGRAM Error;
BEGIN
  writeln('Ошибка при генерации кода: {str(e)}');
END."""

        all_errors.append({
            'type': 'error',
            'line': -1,
            'pos': -1,
            'message': f"Исключение при генерации кода: {str(e)}",
            'source': 'generator'
        })

    print("[==+==] =====================Конец запроса==================== \n")

    # Преобразуем символы в JSON-сериализуемый формат
    def symbols_to_dict(symbols):
        """Рекурсивно преобразует объекты Symbol в словари"""
        result = []
        for symbol in symbols:
            if hasattr(symbol, '__dict__'):
                # Преобразуем объект в словарь
                symbol_dict = {}
                for key, value in symbol.__dict__.items():
                    if isinstance(value, list):
                        # Рекурсивно обрабатываем списки
                        symbol_dict[key] = [symbols_to_dict([item])[0] if hasattr(item, '__dict__') else item
                                            for item in value]
                    else:
                        symbol_dict[key] = value
                result.append(symbol_dict)
            elif isinstance(symbol, dict):
                result.append(symbol)
            else:
                # Простые типы или строки
                result.append(str(symbol))
        return result

    # Получаем символы и преобразуем их
    all_symbols = []
    if hasattr(symbol_table, 'get_all_symbols'):
        symbols = symbol_table.get_all_symbols()
        if symbols:
            all_symbols = symbols_to_dict(symbols)

    # Получаем AST в текстовом виде (если метод существует)
    ast_debug = ""
    if hasattr(parser, 'print_syntax_tree'):
        try:
            # Если метод возвращает строку
            ast_debug = parser.print_syntax_tree()
        except:
            # Если метод только печатает
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                parser.print_syntax_tree()
            ast_debug = f.getvalue()

    # Определяем успешность операции
    success = len(all_errors) == 0

    return jsonify({
        "success": success,
        "pascal_code": pascal_code,
        "errors": all_errors,
        "warnings": all_warnings,
        "symbols": all_symbols,
        "ast_debug": ast_debug if ast_debug else "",
        "ast": ast_json   
    })

@app.route('/validate-plantuml', methods=['POST'])
def validate_plantuml():
    """Эндпоинт для валидации PlantUML кода (только анализ без генерации)"""
    data = request.json

    if not data or 'plantuml' not in data:
        return jsonify({
            "success": False,
            "errors": [{
                'type': 'error',
                'line': -1,
                'pos': -1,
                'message': "Не предоставлен код PlantUML",
                'source': 'request'
            }],
            "warnings": []
        }), 400

    plantuml_code = data.get('plantuml', '')
    all_errors = []
    all_warnings = []

    # Проверяем только лексический и синтаксический анализ
    lexer = PlantUMLLexer(plantuml_code)
    lexer_success = lexer.scan()

    if not lexer_success:
        if hasattr(lexer, 'get_detailed_errors'):
            all_errors.extend(lexer.get_detailed_errors())
        return jsonify({
            "success": False,
            "errors": all_errors,
            "warnings": all_warnings
        })

    parser = PlantUMLSyntaxAnalyzer(lexer)
    parse_success = parser.parse()

    if not parse_success:
        if hasattr(parser, 'get_detailed_errors'):
            all_errors.extend(parser.get_detailed_errors())
        return jsonify({
            "success": False,
            "errors": all_errors,
            "warnings": all_warnings
        })

    # Если нужно, можно добавить семантический анализ
    ast_root = parser.get_syntax_tree()
    semantic_analyzer = SemanticAnalyzer()
    symbol_table, errors, warnings = semantic_analyzer.analyze(ast_root)

    if hasattr(semantic_analyzer, 'get_all_issues'):
        issues = semantic_analyzer.get_all_issues()
        for issue in issues:
            if issue['type'] == 'error':
                all_errors.append(issue)
            elif issue['type'] == 'warning':
                all_warnings.append(issue)

    success = len(all_errors) == 0

    return jsonify({
        "success": success,
        "errors": all_errors,
        "warnings": all_warnings,
        "message": "Валидация завершена" if success else "Найдены ошибки"
    })


if __name__ == '__main__':
    print("=== PlantUML to Pascal Transpiler ===")
    print("Сервер запускается...")
    print("=" * 50 + "\n")

    app.run(debug=True, port=5000)