# ABC notation utils

import wingapi

def _split_with_lineno(txt):
    
    txt = txt.replace('\r\n', '\n')
    retval = []
    parts = txt.split(' ')
    lineno = 0
    for part in parts:
        if part == '':
            continue
        if '\n' in part:
            subparts = part.split('\n')
            for subpart in subparts:
                retval.append((subpart, lineno))
                lineno += 1
            lineno -= 1
        else:
            retval.append((part, lineno))
            
    return retval
        
def abc_paste():
    txt = wingapi.gApplication.GetClipboard()
    txt = txt.replace(':ll', ':|').replace('ll:', '|:').replace('/', '|').replace('||', '|')

    parts = _split_with_lineno(txt)
    
    current_part = 0
    part_start_lineno = 0
    parsed_parts = []
    repeat_parts = []
    for part, lineno in parts:
        
        if lineno > part_start_lineno + 1 and not repeat_parts[current_part]:
            current_part += 1
            part_start_lineno = lineno
            
        if len(parsed_parts) < current_part + 1:
            parsed_parts.append([])
            repeat_parts.append(False)
            
        if len(parsed_parts[current_part]) == 0 and part == '|:':
            repeat_parts[current_part] = True
        elif part == ':|':
            current_part += 1
            part_start_lineno = lineno
        elif part == '|':
            pass
        else:
            parsed_parts[current_part].append(part)
    
    cols = []
    for i, part in enumerate(parsed_parts):

        if repeat_parts[i]:
            p1 = 1
        else:
            p1 = 0
            
        for j, item in enumerate(part):
            if j > 7:
                j -= 8
            if j == 0 or j == len(part) - 1:
                plen = len(item) + p1
            else:
                plen = len(item)
                
            if j + 1 > len(cols):
                cols.append(plen)
            elif plen > cols[j]:
                cols[j] = plen
                
    output = []
    for i, part in enumerate(parsed_parts):
        if i > 0:
            output.append('\n')
        if repeat_parts[i]:
            output.append('|:')
        else:
            output.append('|')
        for orig_j, item in enumerate(part):
            j = orig_j
            if j > 7:
                if j == 8:
                    output.append('\n ')
                    if repeat_parts[i]:
                        output.append(' ')
                j -= 8
            spaces = ' ' * (cols[j] - len(item))
            output.append(' ' + item + spaces + ' ')
            if orig_j < len(part) - 1:
                if j == 7 and repeat_parts[i]:
                    output.append(' ')
                output.append('|')
        if repeat_parts[i]:
            output.append(':|')
        else:
            output.append('|')
            
    txt = ''.join(output)
            
    ed = wingapi.gApplication.GetActiveEditor()
    doc = ed.GetDocument()
    start, end = ed.GetSelection()
    doc.DeleteChars(start, end)
    doc.InsertChars(start, txt)
