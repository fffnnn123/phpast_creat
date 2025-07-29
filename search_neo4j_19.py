import time

from neo4j import GraphDatabase
from openpyxl import Workbook
# 查看函数调用关系，输出成调用链
# 输出到xlsx中


# 设置 Neo4j 连接
neo4j = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "密码"))

queue_1 = '''
MATCH path = (start:Function)-[:CALLS*]->(end:Function)
WHERE start.name = 'copyAddress' AND end.name = 'batchCopy'
RETURN path

MATCH path = (start:Function)-[:CALLS*]->(end:Function)
WHERE start.name = 'editPrivateAddress' AND end.name = 'editData'
RETURN path

MATCH path = (start:Function)-[:CALLS*]->(end:Function)
WHERE start.name = 'aaa' AND end.name = 'ddd'
RETURN path

MATCH (source:Function)
where source.class contains "Controller"
MATCH (sink:Function {name: "connection"})
CALL apoc.algo.allSimplePaths(source, sink, "CALLS>", 5) YIELD path
RETURN path
LIMIT 5

    MATCH (source:Function)
    where source.class contains "Controller"
    MATCH (sink:Function {name: "fwrite"})
    CALL apoc.algo.allSimplePaths(source, sink, "CALLS>", 5) YIELD path
    RETURN path
    LIMIT 5



    MATCH (source:Function)
    where source.class contains "Controller"
    and source.name <> '__construct'
    MATCH (sink:Function)
    where sink.name in {vul_list}
    CALL apoc.algo.allSimplePaths(source, sink, "CALLS>", 5) YIELD path
    where none(n in nodes(path) where n.class <> 'Controller')
    RETURN path
    LIMIT 1000
    
    
    
    MATCH (source:Function)
    where source.class contains "Controller"
    and source.name <> '__construct'
    MATCH (sink:Function)
    where sink.name in {vul_list}
    CALL apoc.algo.allSimplePaths(source, sink, "CALLS>", 5) YIELD path
    WHERE ALL(i IN range(0, size(nodes(path)) - 2) 
          WHERE nodes(path)[i].name <> 'request')
    and length(path) > 1 and nodes(path)[0].namespace = nodes(path)[1].namespace
    RETURN path
    LIMIT 2000
    
    and sink.class = "Php"
    where size(nodes(path)) = 4
'''




session = neo4j.session()


chains = []

datas = []


def search_vul(chains, datas):

    vul_list = ["simplexml_load", "include", "require", "phpinfo", "call_user_func", "file_get_contents", "fopen", "readfile", "fgets", "fread", "parse_ini_file", "highlight_file", "fgetss", "show_source", "system", "passthru", "pcntl_exec", "shell_exec", "curl_exec", "escapeshellcmd", "exec", "unlink", "copy", "fwrite", "file_put_contents", "bzopen", "eval", "assert", "move_uploaded_file", "display"]

    queue_2 = f'''
        
    MATCH (source:Function)
    where source.class contains "Controller"
    and source.name <> '__construct'
    MATCH (sink:Function)
    where sink.name in {vul_list}
    and sink.class = "Php"  
    CALL apoc.algo.allSimplePaths(source, sink, "CALLS>", 6) YIELD path

    RETURN path
    LIMIT 5000

    '''
    result = session.run(queue_2)

# 遍历查询结果
    for record in result:
        data = []
        path = record['path']  # 获取路径

        # 获取路径中的所有节点（即函数），按顺序输出
        function_names = [node['name'] for node in path.nodes]

        # 获取路径中的所有节点的类名，按顺序输出
        class_names = [node['class'] for node in path.nodes]

        # 获取路径中的所有关系（即调用）
        relationships = [rel.type for rel in path.relationships]

        chain = " -> ".join(
            f"{function_names[i]}({class_names[i]}) ({relationships[i]})" for i in range(len(relationships)))
        chain += f" -> {function_names[-1]}({class_names[-1]})"  # 加上最后一个函数
        chains.append(chain)


        for i in range(len(relationships)):
            data.append(function_names[i] + "(" + class_names[i]+ ")" +" (" + relationships[i] +")")


        data.append(function_names[-1] + "(" + class_names[-1] + ")")





        print(chain)

        datas.append(data)

'''
        # 设置输出条件
        try:
            class_key_0 = class_names[0].split("Controller")[0]
            class_key_1 = class_names[1].split("Service")[0]

            if class_key_0 == class_key_1:
                # 输出完整的调用链
                chain = " -> ".join(
                    f"{function_names[i]}({class_names[i]}) ({relationships[i]})" for i in range(len(relationships)))
                chain += f" -> {function_names[-1]}({class_names[-1]})"  # 加上最后一个函数
                chains.append(chain)
                print(chain)
        except:
            pass

        '''

start_time = time.time()
search_vul(chains,datas)
end_time = time.time()
print("查询时间消耗: " + str((end_time - start_time)/60) + "m")
# 关闭连接
neo4j.close()

print(str(datas))

# 使用集合去重 + 保持顺序
seen = set()
xlsx = []
for item in datas:
    t = tuple(item)  # 列表不能哈希，转成元组
    if t not in seen and t is not None:
        seen.add(t)
        xlsx.append(item)

print(str(xlsx))


# 创建一个新的工作簿
wb = Workbook()
ws = wb.active

# 遍历子数组，把每个子数组写成一行
for row in xlsx:
    ws.append(row)

# 保存为 xlsx 文件，需要更改这里的保存路径
wb.save("C:\\Users\\xxx\\Desktop\\output.xlsx")

print("写入成功！")

'''

'''

