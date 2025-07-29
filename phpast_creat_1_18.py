# -*- coding: utf-8 -*-

import time
import subprocess
import csv
import yaml
from phply.phplex import lexer
from phply.phpparse import make_parser
from phply import phpast
import os
import re

from itertools import product




# 版本1_0, 实现查找函数调用链
# 版本1_1，增加了调用链的长度限制，限制1到20个函数调用链长度
# 版本1_2，修复了函数重名导致被调用函数被覆盖，增加类.方法来实现可定义类入口
# 版本1_3
# 版本1_4，使用neo4j，代替内存试图，提高查询速度，目前实现了函数调用查找功能
# 版本1_5，给函数增加类属性
# 版本1_6 增加类属性后，caller到callee对应类存在问题，更改calls_neo4j
# 版本1_7，函数重复时，解决函数类属性没有被遍历全的问题，对于没有自定义的函数，如php自带函数我们添加到了Function
# 版本1_8
# 版本1_9，改变插入neo4j数据方式，利用批量执行，减少执行语句行为，提高效率
# 版本1_10，面对大量数据时，还是非常消耗时间，将使用csv设置节点和调用关系，
# 版本1_11，插入csv的数据存在大量重复的，需要优化插入方式，使用APOC插件加快查询速度
# 版本1_12，优化分析ast结果的方法，确定了$this->aaa()，$this->Api->bbb()，system()写法，目前12的误报率大，但是全
# 版本1_13，优化了namespace，减少误报率，不过存在一些调用链没有查找到
# 版本1_14，优化了继承关系，不过效率太低，扫描某dusoho，70M用时4小时左右，
# 版本1_15，优化了继承关系，提高了一点速度
# 版本1_16，提高了一点速度，70M用时30.903183925151826分钟
# 版本1_17，解决php语法>php5，使用config.ymal忽略解析报错，一次性输出解析报错位置
# 版本1_18，解决没有命令空间问题，或者直接使用function aaa这类情况，修复继承关系的bug，修复php函数定义重复bug，未解决require，
'''

命令是重置neo4j，然后加载csv文件
需要关闭neo4j，然后再启动让neo4j去加载


参考https://neo4j.ac.cn/docs/operations-manual/5/tutorial/neo4j-admin-import/
参考https://neo4j.ac.cn/docs/operations-manual/5/tools/neo4j-admin/neo4j-admin-import/#import-tool-options
注意，SHOW INDEXES; 查看索引

查看节点
MATCH (n) RETURN n LIMIT 10;

查看调用关系
MATCH (start:Function)-[r:CALLS]->(end:Function) RETURN start, r, end LIMIT 10;


删除索引节点和索引
MATCH (n)
DETACH DELETE n;
'''



# 将php高版本转化成php5
def convert_php7_to_php5(php_code):
    # 1
    php_code = re.sub(r'function\s+(\w+)\s*\((.*?)\)\s*:\s*(void|int|float|string|bool|array|callable|iterable)\s*{', r'function \1(\2) {', php_code)

    # 2_1. 替换??为.
    php_code = re.sub(r'\?\?', r' . ', php_code)

    # 3. 移除goto写法
    php_code = re.sub(r'(goto (\w+);)(.*?)(\2[ ]{0,1}:)', r'//\1\3', php_code, flags=re.DOTALL);
    php_code = re.sub(r'(goto (\w+);)', r'//\1', php_code, flags=re.DOTALL);

    # 4. 移除const关键字
    php_code = re.sub(r'(public |protected ){0,1}const[ ]{1,2}[\$](\w+) ', r'public $\2', php_code)

    # 5. 移除protected function getResourceManageClass($type): BaseType 写法
    php_code = re.sub(r'\): (\w+)\n', r')', php_code);

    # 6. 移除if ($this->getCourseMemberService()->hasRoleByMember($member, ...$course['joinRoles'])) { 写法
    php_code = re.sub(r'\.\.\.\$', r'$', php_code, flags=re.DOTALL);

    # 7. 移除 [$courseItems, $pluginItemIds] = $this->filterPluginTask($courseId); 写法
    php_code = re.sub(r'\[\$(\w+), \$(\w+)] =', r'$php_tihuan = ', php_code, flags=re.DOTALL);

    # 8. 移除 public static function getCodeMessage($code) : ?string 写法
    php_code = re.sub(r'\)[ ]{0,1}: \?(\w+)', r')', php_code);

    # 9. 移除 public function getByPopupTypeAndUserId(string $popupType, ?int $userId); 写法
    php_code = re.sub(r' \?((\w+) \$)', r'\1', php_code, flags=re.DOTALL);

    # 10. 移除...$ 写法
    php_code = re.sub(r'\.\.\.\$', r'$', php_code, flags=re.DOTALL);

    # 11. 移除 public function hasCourse() : bool; 写法
    # public function canStartSyncById($recordId) : bool;
    # public function hasTargetPlanResult($projectPlanId, $userId = null): bool;
    php_code = re.sub(r'function (\w+)\(([$\w\+), =]{0,50})\)[ ]{0,1}: (\w+);', r'function \1(\2);', php_code, flags=re.DOTALL)

    # 12. 移除 use function MongoDB\BSON\fromJSON; 写法
    php_code = re.sub(r'use (\w+) ', r'use ', php_code, flags=re.DOTALL)

    # 13. 移除 \App\EofficeApp\Charge\Constants\Attribute::CHARGE_STATISTIC_DIMENSION[3];
    # eo_trans(\App\EofficeAttribute::CHARGE_DIMENSION_TEXT[\App\EofficeApp\Ctribute::CHARGE_DIMENSION_X1][$statisticData["x1"]]);
    php_code = re.sub(r'::([\w]{0,50})(\[\d+\])', r'::\1', php_code, flags=re.DOTALL)
    php_code = re.sub(r'::([\w]{0,50})\[\S+\]([ );]{1})', r'::\1\2', php_code, flags=re.DOTALL)

    # 14. 替换php关键字函数，如public function list()
    php_code = re.sub(r'function [list]{4}\(', r'function list_replace(', php_code, flags=re.DOTALL)

    # 15. 替换app("App\\EofficeApp\\LogCenter\\Facades\\LogCenter")::syncLog();为)->syncLog()
    php_code = re.sub(r'\)::([\w]{0,50})\((.*?)\);', r')->\1(\2);', php_code, flags=re.DOTALL)

    # 16. isset(self::PARSERS[$suffix])
    # if(isset($groupedMatchWords[\App\EofficeApp\SensitiveWord\Constants\SensitiveWord::HANDLE_METHOD_DESENSITIZE]))
    php_code = re.sub(r'isset\([$]{0,1}(\S*?)::[$]{0,1}(\S*?)\)', r'isset($\1\2)', php_code, flags=re.DOTALL)
    php_code = re.sub(r'isset\(\$\\(\S*)\\(\w*?)', r'isset($\2', php_code, flags=re.DOTALL)

    # 17. return $this->returnResult($this->iWebOfficeService->strtolower($params["OPTION"])($params, $this->request->file("MsgFileBody"), $this->own));
    php_code = re.sub(r'\)\(', r'), $self_replace(', php_code, flags=re.DOTALL)

    # 18. 替换$code = $key = (DNS1DFacade::getBarcodeArray())['code'];
    php_code = re.sub(r' \((\S*?)::(\S*?)\)\[', r'\2 . $self_replace[', php_code, flags=re.DOTALL)

    # 19. $objectName = app(\App\EofficeApp\Charge\Constants\Service::DEPARTMENT)->getDeptNameByIds([$objectId])[$objectId] ?? "";
    php_code = re.sub(r' (\w*?)\((\S*?)::(\S*?)->(\w*?)(\S*?)\)\[', r'\1() . \5) . $self_replace[', php_code, flags=re.DOTALL)

    # 20. 替换$self_replace($params);
    #php_code = re.sub(r'\$(\w*?)\(\$', r'$self_replace->\1(', php_code, flags=re.DOTALL)

    # print(php_code)
    return php_code



error_lists = []
# 解析php文件
def parse_php_file(file_path):
    global error_lists
    # 创建解析器
    parser = make_parser()
    ast = None
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    with open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
        php_code = file.read()


        php_code = convert_php7_to_php5(php_code)
        # 解析 PHP 代码为 AST
        # lexer是 phply 提供的词法分析器，用于将 PHP 代码转换为词法单元
        try:
            ast = parser.parse(php_code, lexer=lexer.clone())

        except SyntaxError as e:
            print(f"Error: {e.msg}")
            print(f"Line: {e.lineno}, Column: {e.offset}")

            if e.lineno in config['error_line']:
                pass
            else:
                error_lists.append([file_path, e.lineno])

        if ast:
            print("parse_php_file: \n" + str(ast) + "\n")

            return ast
        else:
            return False

namespace = ""
# 解析多个 PHP 文件
def parse_multiple_files(directory):

    functions_define = {}
    function_calls = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.php'):
                file_path = os.path.join(root, file)
                print(f"Parsing: {file_path}")
                # 解析成ast
                ast_tree = parse_php_file(file_path)
                if ast_tree is not False:
                    # 获取函数调用
                    get_function_calls_from_ast(ast_tree)

                else:
                    pass


    with open('error_lists.txt', 'w+') as f:
        for i in error_lists:
            f.write(str(i[0]) + ": " + str(i[1]) + "\n")


function_calls_neo4j = []
function_calls_neo4j_count = 0
calls_neo4j = []
assignments = []

classes = ""


# 获取函数调用
def get_function_calls_from_ast(nodes):
    global calls_neo4j
    global assignments
    global namespace
    global classes

    use_namespace = []


    # 通过
    def traverse(node, current_function="", extends=""):
        global function_calls_neo4j_count
        global namespace
        global classes


        print("子节点： " + str(node))
        print("子节点属性： " + str(type(node)))

        if isinstance(node, phpast.Namespace):
            print("namespace: " + node.name)
            namespace = node.name
            use_namespace.append(node.name)

        elif isinstance(node, phpast.UseDeclarations):
            print("UseDeclarations: " + node.nodes[0].name)
            use_namespace.append(node.nodes[0].name)

        elif isinstance(node, phpast.Class) or isinstance(node, phpast.Trait):
            print("classes: " + node.name)
            classes = node.name
            try:
                extends = node.extends
            except:
                pass

        elif isinstance(node, phpast.Method) \
                or isinstance(node, phpast.Function):

            print("Method: " + str(node))
            # 记录函数定义
            # functions[classes + "." + node.name] = node
            # 先有函数定义，再有函数调用，因此这里记录函数名，为记录调用函数做准备
            current_function = node.name  # 当前函数的名称

            # 这里会覆盖一个函数调用相同函数，不过不影响
            function_calls_neo4j_count += 1
            function_calls_neo4j.append((function_calls_neo4j_count, str(node.name), str(classes), str(namespace), ",".join(use_namespace), extends, "Function"))

        # 调用系统函数
        elif  isinstance(node, phpast.FunctionCall):

            calls_neo4j.append((function_calls_neo4j_count, [str(node.name), "Php", [str(classes), str(namespace)]], "CALLS"))

        # 调用静态函数
        elif isinstance(node, phpast.StaticMethodCall):
            calls_neo4j.append((function_calls_neo4j_count, [str(node.name), node.class_, []], "CALLS"))

        elif isinstance(node, phpast.MethodCall):
            print("FunctionCall: " + str(node))
            print("FunctionCall属性: " + str(type(node)))
            print("FunctionCall其中node.name: " + str(node.name))
            print("FunctionCall其中node.name属性: " + str(type(node.name)))
            print("FunctionCall其中current_function: " + current_function)

            # 记录调用函数和被调用函数
            # calls.append((classes + "." + current_function, node.name))
            if isinstance(node.node, phpast.Variable) and node.node.name == '$this':
                calls_neo4j.append((function_calls_neo4j_count, [str(node.name), classes, use_namespace], "CALLS"))
            elif isinstance(node.node, phpast.ObjectProperty) and isinstance(node.node.node, phpast.Variable) and node.node.node.name == '$this':
                try:
                    calls_neo4j.append((function_calls_neo4j_count, [str(node.name), node.node.name.lower(), use_namespace], "CALLS"))
                except:
                    # 解决写法问题 $data = $this->{$repository}->getOutSendDataLists($param);
                    calls_neo4j.append((function_calls_neo4j_count, [str(node.name), node.node.name.name.lower(), use_namespace], "CALLS"))
            else:
                calls_neo4j.append((function_calls_neo4j_count, [str(node.name), "None", use_namespace], "CALLS"))

        # 递归遍历子节点
        # 检查节点是否有子节点属性
        if hasattr(node, '__dict__'):

            print("子节点为__dict__属性: " + str(node))
            for child in node.__dict__.values():

                print("child: " + str(child))
                if isinstance(child, list):
                    print("child为list: " + str(child))
                    # 如果子节点是列表，逐个处理
                    for subchild in child:
                        # 如果是单个子节点

                        if isinstance(subchild, phpast.Node):

                            traverse(subchild, current_function, extends)
                elif isinstance(child, phpast.Node):
                    # 如果是单个子节点

                    traverse(child, current_function, extends)

    for node in nodes:

        traverse(node)

    namespace = ""
    classes = ""


    # 这里的functions，存在两个部分，一部分是类+函数名，另一部分是node节点
    # print("functions: " + str(functions))
    # 也存在两部分，，一部分是类+函数名，另一部分是被调用函数
    # print("calls: " + str(calls))




def delete_files_in_directory(directory):
    # 获取目录下的所有文件和子目录
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # 判断是否为文件，若是文件则删除
        if os.path.isfile(file_path):
            os.remove(file_path)


# 示例调用

def run_neo4j_admin_import(nodes_file, relationships_file):

    # print("删除数据库文件完成")
    # 构造 neo4j-admin import 命令（确保参数格式正确）
    command = [
        "neo4j-admin.bat", "database", "import", "full", "neo4j",
        "--overwrite-destination",
        "--verbose",
        f"--nodes={nodes_file}",
        f"--relationships={relationships_file}"
    ]

    # 执行命令
    print("执行导入")

    result = subprocess.run(command, capture_output=True, text=True)
    print("Import successful:", result.stdout)
    print("Import successful:", result.stderr)








start_time = time.time()

parse_multiple_files("D:\\src\\")

end_time = time.time()
print("分析消耗: " + str((end_time-start_time)/60) + "分钟")

start_time_csv = time.time()



not_define_func = []
start_num = []
not_define_func_nums = []


# function_calls_neo4j更新namespace
len_all = len(function_calls_neo4j)
# 提前计算并存储需要检查的字段，减少重复计算
processed_calls = [(fc[3] + "\\" + fc[2], fc) for fc in function_calls_neo4j]

for m, n in product(range(len_all), repeat=2):
    call_m = processed_calls[m]
    call_n = processed_calls[n]

    # 比较字符串是否存在于另一个字符串中
    if call_n[0] in call_m[1][4]:
        # 更新 m 的数据
        list_m = list(call_m[1])

        list_m[4] = function_calls_neo4j[m][4] + "," + call_n[1][4]

        function_calls_neo4j[m] = tuple(list_m)
'''
    elif call_m[0] in call_n[1][4]:
        # 更新 n 的数据
        list_n = list(call_n[1])
        list_n[4] = list_n[4] + "," + call_m[1][4]
        function_calls_neo4j[n] = tuple(list_n)
'''
        # function_calls_neo4j[n] = (function_calls_neo4j[n][0], function_calls_neo4j[n][1], function_calls_neo4j[n][2], function_calls_neo4j[n][3], function_calls_neo4j[n][4] + function_calls_neo4j[m][4], function_calls_neo4j[n][5], function_calls_neo4j[n][6])
# print("更新namespace后: " + str(function_calls_neo4j))

# 更新calls_neo4j中被调用函数所在的namespace
function_calls_dict = {fc[0]: fc for fc in function_calls_neo4j}
len_all_call = len(calls_neo4j)
for y in range(len_all_call):
    call = calls_neo4j[y]
    call_key = call[0]

    if call_key in function_calls_dict:
        # 获取对应的 function_calls_neo4j 数据
        function_call = function_calls_dict[call_key]
        # 将元组转为列表，修改相应的数据
        list_call = list(call)
        list_call[1][2] = list_call[1][2] + function_call[4].split(",")
        # 更新回元组
        calls_neo4j[y] = tuple(list_call)

# print("更新call后: " + str(calls_neo4j))

# print("function_calls_neo4j: " + str(function_calls_neo4j))
# print("calls_neo4j: " + str(calls_neo4j))
function_calls_neo4j_csv = [(":ID", "name", "class", "namespace", "use_namespace", "extends", ":LABEL")] + function_calls_neo4j
calls_neo4j_csv = [(":START_ID", ":END_ID", ":TYPE")]

php_func = []
php_func_num = []
#print(str(calls_neo4j))
for num in range(len(calls_neo4j)):
    switch = 1

    callee_id = []

    for i in function_calls_neo4j:

        if calls_neo4j[num][1][1] == "Php" and calls_neo4j[num][1][2] == ['', '', ''] and calls_neo4j[num][1][0] == i[1]:
            switch = 0
            calls_neo4j_csv.append((calls_neo4j[num][0], i[0], "CALLS"))


        # 函数和类在函数定义中
        if [i[1], i[2]] == [calls_neo4j[num][1][0], calls_neo4j[num][1][1]] or [i[1], i[2].lower()] == [calls_neo4j[num][1][0], calls_neo4j[num][1][1]]:
            switch = 0
            try:
                if str(i[3] + "\\" + i[2]) in calls_neo4j[num][1][2] or calls_neo4j[num][1][2][0] == i[3]:
                    calls_neo4j_csv.append((calls_neo4j[num][0], i[0], "CALLS"))

            except IndexError:
                calls_neo4j_csv.append((calls_neo4j[num][0], i[0], "CALLS"))

            break

        # 函数在函数定义中，但是类为None的情况
        elif i[1] == calls_neo4j[num][1][0] and calls_neo4j[num][1][1] != "Php":

            try:
                if str(i[3] + "\\" + i[2]) in calls_neo4j[num][1][2] or calls_neo4j[num][1][2][0] == i[3]:
                    callee_id.append(i[0])

            except IndexError:
                callee_id.append(i[0])

    # 如果函数是php自带的，那么添加到函数定义中，并添加调用关系
    if calls_neo4j[num][1][1] == "Php" and calls_neo4j[num][1][2] != ['', '', '']:
        switch = 0
        if calls_neo4j[num][1][0] not in php_func:
            # print("aaa" + str(calls_neo4j))


            function_calls_neo4j_count += 1
            php_func.append(calls_neo4j[num][1][0])
            php_func_num.append(function_calls_neo4j_count)
            function_calls_neo4j_csv.append((function_calls_neo4j_count, calls_neo4j[num][1][0], "Php", "None", "", "", "Function"))
            calls_neo4j_csv.append((calls_neo4j[num][0], function_calls_neo4j_count, "CALLS"))
        else:
            calls_neo4j_csv.append((calls_neo4j[num][0], php_func_num[php_func.index(calls_neo4j[num][1][0])], "CALLS"))


    # 函数在函数定义中，但是类为None的情况，添加调用关系
    if switch == 1 and callee_id != []:
        for id in callee_id:
            calls_neo4j_csv.append((calls_neo4j[num][0], id, "CALLS"))




    # 当被调用函数没有在函数定义中找到，那么添加函数定义，添加调用关系
    if switch == 1 and callee_id == []:

        # 防止添加重复的未定义的函数定义
        if calls_neo4j[num][1][0] not in not_define_func:
            not_define_func.append(calls_neo4j[num][1][0])
            function_calls_neo4j_count += 1
            not_define_func_nums.append((calls_neo4j[num][1][0], function_calls_neo4j_count))

            function_calls_neo4j_csv.append((function_calls_neo4j_count, calls_neo4j[num][1][0], "None", "None", "", "", "Function"))
            calls_neo4j_csv.append((calls_neo4j[num][0], function_calls_neo4j_count, "CALLS"))
        else:
            for end_num in not_define_func_nums:
                if end_num[0] == calls_neo4j[num][1][0]:
                    calls_neo4j_csv.append((calls_neo4j[num][0], end_num[1], "CALLS"))


end_time_csv = time.time()
# print("function_calls_neo4j_csv: " + str(function_calls_neo4j_csv))
# print("calls_neo4j_csv: " + str(calls_neo4j_csv))
print("生成数据消耗: " + str((end_time_csv - start_time_csv)/60) + "分钟")


# print("function_calls_neo4j_csv: " + str(function_calls_neo4j_csv))
# print("calls_neo4j_csv: " + str(calls_neo4j_csv))


start_time_neo4j = time.time()
# 调用函数执行导入
# 打开（或创建）CSV 文件进行写入
print("开始导入")
f_functions = open("functions.csv", mode="w+", newline='', errors='ignore', encoding='utf-8')
writer_functions = csv.writer(f_functions)
writer_functions.writerows(function_calls_neo4j_csv)  # 写入多行数据
f_functions.close()

f_functions_calls = open("function_calls.csv", mode="w+", newline='', errors='ignore', encoding='utf-8')
writer_functions_calls = csv.writer(f_functions_calls)
writer_functions_calls.writerows(calls_neo4j_csv)  # 写入多行数据
f_functions_calls.close()

# 这里是/py文件运行根目录+functions.csv、functions.csv
run_neo4j_admin_import("D:/py文件运行根目录/functions.csv", "D://py文件运行根目录、function_calls.csv")
print("导入完成")
end_time_neo4j = time.time()
print("写入xml，导入neo4j消耗: " + str((end_time_neo4j-start_time_neo4j)/60) + "分钟")

