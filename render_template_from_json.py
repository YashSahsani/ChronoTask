import html
def render_html_from_json(template_data):
    html_parts = []
    for block in template_data:
        content = html.escape(block['content'])  # Escape here
        if block['type'] == 'heading':
            html_parts.append(f"<h2>{content}</h2>")
        elif block['type'] == 'textarea':
            html_parts.append(f"<p>{content}</p>")
        elif block['type'] == 'datetime':
            html_parts.append(f"<p><strong>Date/Time:</strong> {content}</p>")
        elif block['type'] == 'checkbox':
            html_parts.append(f"<label><input type='checkbox' disabled> {content}</label><br>")
        elif block['type'] == 'radio':
            html_parts.append(f"<label><input type='radio' disabled> {content}</label><br>")
        elif block['type'] == 'table':
            table_html = ''
            for row in block['content']:
                row_html = ''.join(f"<td>{html.escape(cell)}</td>" for cell in row)
                table_html += f"<tr>{row_html}</tr>"
            html_parts.append(f"<table border='1' cellpadding='5' cellspacing='0'>{table_html}</table><br>")
    return ''.join(html_parts)