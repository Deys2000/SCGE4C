import os

from tree_sitter import Language, Parser
import tree_sitter_c as tsc

import pydot

C_LANGUAGE = Language(tsc.language())
parser = Parser(C_LANGUAGE)

# Step 1: Recursively collect .c and .h files
def collect_files(directory):
    c_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.c', '.h')):
                c_files.append(os.path.join(root, file))
    return c_files

# Step 2: Analyze includes, ifdefs, and function definitions
def analyze_files(files):
    functions = {}
    includes = {}
    externs = set()

    for file_path in files:
        with open(file_path, 'r') as f:
            source_code = f.read()

        tree = parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node

        # Extract function definitions and #include directives
        functions[file_path] = extract_function_definitions(root_node, file_path)
        
        if file_path not in includes:
            includes[file_path] = [] 
        extract_includes(file_path, includes, root_node)
        
        externs.update(extract_externs(root_node))
    
    # create backlinks from all .h files to .c files
    for cfile in includes:
        if cfile.endswith('.c'):
            for hfile in includes[cfile]:
                if hfile.endswith('.h'):
                    includes[hfile].append(cfile)

    return functions, includes, externs

# Extract function definitions
def extract_function_definitions(node, file_path):
    definitions = []
    if node.type == 'function_definition':
        func_name = node.child_by_field_name('declarator').text.decode('utf-8')
        definitions.append((func_name))
    for child in node.children:
        definitions.extend(extract_function_definitions(child, file_path))
    return definitions

# Extract #include directives
def extract_includes(file_path, includes, node):
    # TODO: might be best to gather include with regex rather than AST for performance sake
    if node.type == 'preproc_include':
        include_text = node.text.decode('utf-8')#.strip('"<>')
        if '\"' in include_text: # include only files that are part of source code, not system libraries            
            include_text = include_text.replace('"', '') # remove paranthesis
            include_text = include_text.replace('#include', '') # remove paranthesis
            include_text = include_text.strip('\n ') # remove trailing newline and space
            # at this point include_text should be a pure path to the included file
            
            if ( include_text.endswith('.h') or include_text.endswith('.c')) :         
                dir_path = os.path.dirname(file_path)       
                includes[file_path].append(dir_path+"\\"+include_text)

    for child in node.children:
        extract_includes(file_path, includes, child)

# Extract extern declarations
def extract_externs(node):
    externs = set()
    if node.type == 'declaration' and 'extern' in node.text.decode('utf-8'):
        externs.add(node.text.decode('utf-8'))
    for child in node.children:
        externs.update(extract_externs(child))
    return externs

# Step 3: Analyze function calls
def analyze_function_calls(files, functions, includes):
    
    call_graph = {}


    for file_path in files:
        # parse file for AST
        with open(file_path, 'r') as f:
            source_code = f.read()
        tree = parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node
        
        # 1. go through file AST to get all function->callee into a graph (mapping of key->set)
        calls_in_file = {}
        extract_function_calls(root_node, calls_in_file )    
        print(calls_in_file)

        # 2. go through includes graph to get scope of file to search into a set
        files_in_scope = set(); files_in_scope.add(file_path)
        seen = set(); seen.add(file_path)
        get_all_included_files(files_in_scope, seen, file_path, includes)
        print("FIS",files_in_scope)

        # 3. go through the calls set to search for the existence of a function with the same name in the scope set
        file_call_graph = {}
        map_caller_to_callee(file_call_graph, calls_in_file, functions, files_in_scope)
        print(file_call_graph)

        # 4. update the overall call graph with the call graph of this file
        populate_call_graph( call_graph, file_call_graph, file_path) 

    return call_graph

def populate_call_graph( call_graph, file_call_graph, file_path):         
        for func in file_call_graph:
            for mapping in file_call_graph[func]:
                
                idx_par = func.find("(")                                
                func_name = func[:idx_par]

                if file_path+"::"+func_name not in call_graph:
                    call_graph[file_path+"::"+func_name] = []                
                
                call_graph[file_path+"::"+func_name].append(mapping)


def extract_function_calls(node, calls_in_file, current_function=None):

    if node.type == 'function_definition':
        # Set the current function scope
        current_function = node.child_by_field_name('declarator').text.decode('utf-8')
    elif node.type == 'call_expression' and current_function:
        function_call = node.child_by_field_name('function').text.decode('utf-8')    
        if current_function not in calls_in_file:
            calls_in_file[current_function] = set()
        calls_in_file[current_function].add(function_call)
        
    for child in node.children:
        extract_function_calls(child, calls_in_file, current_function)

def get_all_included_files(files, seen, file_path, includes):
    for file in includes[file_path]:
        if( file in seen ):
            continue
        elif( file.endswith('.c')):
            seen.add(file)
            files.add(file)
            
        else:
            seen.add(file)
            get_all_included_files(files, seen, file, includes)

def map_caller_to_callee(file_call_graph, calls_in_file, functions, files_in_scope):    

    def find_callee_implementation(callee, functions, files_in_scope):        
        #TODO: have heiarchy of search from current file -> extern -> includes scope. Unsure if this is useful
        for file in files_in_scope:
            for func in functions[file]:
                # get location of "(" in order to extract pure function name from the function signature
                idx = func.find('(')                
                if( func[:idx] == callee):
                    return file+"::"+callee
        return None

    def add_mapping(file_call_graph, caller, callee_found):
        if caller not in file_call_graph:
            file_call_graph[caller] = set()
        file_call_graph[caller].add(callee_found)


    for caller in calls_in_file:
        for callee in calls_in_file[caller]:
            callee_found = find_callee_implementation(callee, functions, files_in_scope)
            if callee_found:
                add_mapping(file_call_graph, caller, callee_found)
    
# Step 4: Output graph
def output_graph(graph, output_path='call_graph.dot'):
    with open(output_path, 'w') as f:
        f.write('digraph G {\n')
        for node in graph:
            for neighbor in graph[node]:
                f.write(f'  "{node}" -> "{neighbor}";\n')
        f.write('}\n')
    print(f'Call graph written to {output_path}')

    
def output_steps(directory, files, functions, includes, externs, calls, output_path='steps.log'):
    with open(output_path, 'w') as f:
        f.write(f'Directory: {directory}\n\n')
        f.write('Files:\n')
        for file in files:
            f.write(f'  - {file}\n')
        f.write('\n')

        f.write('Function Implementations:\n')
        for func in functions:
            f.write(f'  - {func} - {functions[func]}\n')
        f.write('\n')

        f.write('Bidirectional Includes Graph:\n')
        for include in includes:
            f.write(f'  - {include} - {includes[include]}\n')
        f.write('\n')

        f.write('Externs:\n')
        for extern in externs:
            f.write(f'  - {extern}\n')
        f.write('\n')

        f.write('Calls:\n')
        for call in calls:
            f.write(f'  - {call} - {calls[call]}\n')
        f.write('\n')
    print(f'Steps and results written to {output_path}')
    
# Main
if __name__ == "__main__":
    directory = ".\\temp"
    files = collect_files(directory)
    functions, includes, externs = analyze_files(files)    
    call_graph = analyze_function_calls(files, functions, includes)    

    output_steps(directory, files, functions, includes, externs, call_graph)
    output_graph(call_graph)
