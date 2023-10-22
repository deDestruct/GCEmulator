from abc import ABC, abstractmethod
import enum
import os
import sys
import time
from random import shuffle

class GCType(enum.Enum):
    MARK = 1
    LINK = 2

class DefragType(enum.Enum):
    DISABLE = 1
    ENABLE = 2

SLEEP_TIME = 0.01

class Node(ABC):
    def __init__(self, name) -> None:
        #*****OBJ INFORMATION*****

        self.name = name
        self._children = []
        # self.parrent = []

        #*****SYSTEM INFORMATION (EMULATION)*****

        self.memory_addr = None # TODO  1. Проставить адреса при распределение по памяти объектов
                                #       2. Добавить в документации пункт, что адреса нужны только для модели!
        self.children_addr = [] # массив для эмуляции ссылок
    
    @staticmethod
    def nodeCreator(name, node_type):
        if node_type == GCType.MARK:
            return NodeMark(name)
        elif node_type == GCType.LINK:
            return NodeLink(name)
        return None
    @staticmethod
    def nodeClone(node):
        if isinstance(node, NodeMark):
            return NodeMark(node.name)
        elif isinstance(node, NodeLink):
            return NodeLink(node.name)
        return None

    @abstractmethod
    def postInit(self):
        pass
    @abstractmethod
    def isGarbage(self):
        pass
    @abstractmethod
    def getName(self):
        pass
    @abstractmethod
    def deleteMe(self):
        pass
    @abstractmethod
    def setFree(self):
        pass
    def addChild(self, child):
        self._children.append(child)
        # child.addParrent(self)
    def removeChild(self, child):
        if child in self._children:
            self._children.remove(child)

    def getChildren(self):
        return self._children
    def setMemoryAddr(self, new_addr):
        self.memory_addr = new_addr
    def getMemoryAddr(self): # NEW
        return self.memory_addr

    def generateChildrenMemoryAddrTable(self): # NEW (using one time after memory addr init)
        self.children_addr = []
        for o in self._children:
            child_addr = o.getMemoryAddr()
            self.children_addr.append(child_addr)
    def updateChildrenMemoryAddrTable(self, addr_table): # NEW
        for i in range(len(self.children_addr)):
            if self.children_addr[i] in addr_table:
                self.children_addr[i] = addr_table[self.children_addr[i]]
        pass 
    def printMe(self):
        pass
    '''
    def addParrent(self, parrent):
        self.parrent.append(parrent)
    '''

class NodeMark(Node):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.mark = False
    
    def postInit(self):
        self.mark = True

    def isGarbage(self):
        return not(self.mark)
    
    def getName(self):
        return f'{self.name}'

    def deleteMe(self):
        pass

    def setFree(self):
        self.mark = False

    def getNotMarkedChildren(self):
        not_marked_children = []
        for child in self._children:
            if not(child.mark):
                not_marked_children.append(child)
        return not_marked_children
    
    def printMe(self):
        print(f'Node: {self.name}')
        print('Children: ', end='')
        for c in self._children:
            print(f'{c.name} ', end='')
        print()
        print(f'Marked: {self.mark}')
        print('--------')

class NodeLink(Node):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.link = 0
    
    def postInit(self):
        self.link += 1

    def isGarbage(self):
        return self.link == 0

    def getName(self):
        return f'{self.name}({self.link})'

    def unlinkMe(self): # TODO переименоват на unlink
        for c in self._children:
            c.link -= 1
        self.link = 0
    
    def deleteMe(self): # для совместимости
        self.unlinkMe()

    def setFree(self):
        self.link = 0

    def printMe(self):
        print(f'Node: {self.name}')
        print('Children: ', end='')
        for c in self._children:
            print(f'{c.name} ', end='')
        print()
        print(f'Link: {self.link}')
        print('--------')

class GarbageCollector():
    def __init__(self, mApi, gc_type, defrag_type=DefragType.ENABLE):
        self.mApi = mApi
        self.gc_type = gc_type
        self.defrag_type = defrag_type
        self.count = 0

    def collectGarbage(self):
        start_time = time.time()
        if self.gc_type == GCType.LINK: 
            self.mApi.displayAllObj()
            # дополнителная проверка на правильность поднятого графа для ссылочного метода
            for o in self.mApi.all_obj:
                time.sleep(SLEEP_TIME)
                self.count += 1
                if o.isGarbage():
                    o.unlinkMe()
            gc_time = time.time() - start_time
            print('* Start memory state *')
            self.mApi.memoryView(start=True)
            print(f'* After link method *')
            self.mApi.memoryView()

        elif self.gc_type == GCType.MARK:
                print('* Start memory state *')
                self.mApi.memoryView(start=True)
                self.sweep()
                self.mark()
                gc_time = time.time() - start_time
                print('* After mark method *')
                self.mApi.displayAllObj()
                self.mApi.memoryView()

        # Defragmentation switch ***ADD***
        if self.defrag_type == DefragType.ENABLE:
            self.mApi.defragmentation()
        # Time out switch **ADD**
        print(f'*****GC TIME: {round(gc_time*1000, 2)} ms.*****')


    # маркировка объектов
    def mark(self, stack=[], start = 1):
        if start:
            stack = [*self.mApi.program_obj]
        if len(stack) == 0:
            return 
        for o in stack:
            #print(o.name, end=" ")
            pass
        #print('\n')
        obj = stack[-1]
        obj.mark = True
        stack.pop(-1)
        
        self.count += 1
        time.sleep(SLEEP_TIME)

        stack = [*stack, *obj.getNotMarkedChildren()]

        return self.mark(stack, 0)

    def sweep(self):
        all_obj = [*self.mApi.all_obj]
        for o in all_obj:
            time.sleep(SLEEP_TIME)
            self.count += 1
            o.mark = False


class MemoryApi():
    def __init__(self, file, gc_type, size = 20, debug = 1) -> None:
        self.memory = [0]*size
        self.program_obj = []   # массив типа Node
        self.all_obj = []       # массив типа Node
        self.addr_table = {}    # hash-table с новыми адресами объектов в памяти (для дефрегментации)

        self.gc_type = gc_type

        self.debug = debug

        print(f'Openning graph {file}')
        print(f'Using {gc_type}')
        self.displayLegend()
        print('\n\n* Empty memory *')
        self.memoryView()
        self.__loadMemoryState(file, gc_type)


    def __memoryInitilization(self):
        if len(self.all_obj) > len(self.memory):
            print('Not enought memory!')
            print('Exiting...')
            sys.exit(1)
        for i in range(len(self.all_obj)):
            self.memory[i] = self.all_obj[i] 
        shuffle(self.memory)
        self.__setAddr()
    
    def memoryView(self, start = False):
        pallete = ['\x1b[32m', '\x1b[32m', '\x1b[31m']
        if start:
            pallete = ['\x1b[32m', '\x1b[34m', '\x1b[34m']
        print('='*20)
        print('[ ',end='')

        count = 0

        for c in self.memory:
            if c == 0:
                print(f'{pallete[0]}# \x1b[0m', end=' ') # green
            else:
                if c.isGarbage() == 1: 
                    print(f'{pallete[1]}{c.getName()} \x1b[0m', end=' ') #green
                else:
                    print(f'{pallete[2]}{c.getName()} \x1b[0m', end=' ') #red

            if count == 40:
                print('\n\n', end='  ')
                count = 0
            else:
                count+=1

            
        print(']')
        print('='*20)

    #Deprecated#
    def deleteObject(self, obj):
        print(f'Delete: {obj.name}')

        obj.deleteMe()

        if obj in self.program_obj:
            self.program_obj.remove(obj)
            return
        for o in self.all_obj:
            if o != obj:
                o.removeChild(obj)

    def defragmentation(self):
        print('* Defragmentation *')
        free_cell = 0 # адрес в памяти последнего свободного элемента
        start_time = time.time()
        for i in range(len(self.memory)):
            time.sleep(SLEEP_TIME)
            if type(self.memory[i]) != int:
                if not(self.memory[i].isGarbage()):
                    if i != free_cell:
                        self.memory[free_cell] = self.memory[i]                         # сдвиг объекта в свободный участок памяти
                        self.addr_table[self.memory[i].getMemoryAddr()] = free_cell     # добавление пары ключ:значение, где ключ старый адрес памяти, значение новый адрес
                        self.memory[free_cell].setMemoryAddr(free_cell)                 # измение в объекте значения адреса в памяти на новый
                        self.memory[i] = Node.nodeClone(self.memory[free_cell])         # объект 'пустышка' на старом адресе объекта (показать, что данные не исчезают из памяти, если их намеренно не перезаписать)
                        free_cell += 1
                    else:
                        free_cell += 1 # next cell, do nothing
            #self.memoryView()
        for o in self.all_obj:
            time.sleep(SLEEP_TIME)
            if not(o.isGarbage()):
                o.updateChildrenMemoryAddrTable(self.addr_table)
        #self.__setAddr()
        defrag_time = time.time()-start_time
        #self.displayDefragHashMap() deprecated
        self.displayDefragChanges()
        self.addr_table = {}                    
        self.memoryView()
        print(f'*****DEFRAG TIME: {round(defrag_time*1000, 2)} ms.*****')
        pass

    def __setAddr(self):
        for i in range(len(self.memory)):
            if type(self.memory[i]) != int:
                self.memory[i].setMemoryAddr(i)
        for o in self.all_obj:
            o.generateChildrenMemoryAddrTable()

    def __loadMemoryState(self, file, node_type):
        with open(file, 'r') as f:
            graph_count = int(f.readline())
            f.readline() # пропуск пустой строки
            c = 0 # count of objects
            for g in range(graph_count):
                line = f.readline()

                obj_count = len(line)-1 # count of object in current graph
                c+=1
                program_node = Node.nodeCreator(f'ROOT_N{c}', node_type)
                program_node.postInit()
                self.all_obj.append(program_node)
                self.program_obj.append(program_node)

                for i in range(1, obj_count):
                    c+=1
                    self.all_obj.append(Node.nodeCreator(f'N{c}', node_type))
                for i in range(0, obj_count):
                    #print(line)
                    for y in range(obj_count):
                        if line[y] == '1':
                            #print(i, y)
                            child_node = self.all_obj[y-obj_count]
                            self.all_obj[i-obj_count].addChild(child_node)
                            child_node.postInit()
                    line = f.readline()

        self.__memoryInitilization()
        
        print('\n* Loading data... *')
        #self.displayAllObj() # после поднятия из файла, выводим структуру памяти
        

    def displayAllObj(self): # for debug
        if self.debug == 0:
            return 0
        print('\n###ALL OBJECTS###')
        for o in self.all_obj:
            o.printMe()
        print('\n###PROGRAM OBJECTS###')
        for o in self.program_obj:
            o.printMe()
    def displayDefragChanges(self):
        print(' ~ new memory addresses ~ ')

        new_addrs = list(self.addr_table.values())
        old_addrs = list(self.addr_table.keys())

        for o in self.all_obj:
            if o.isGarbage():
                continue # skip 'garbage' obj
            name = o.name
            cur_obj_addr = o.getMemoryAddr()
            children = o.getChildren()

            if cur_obj_addr in new_addrs:
                old_obj_addr = old_addrs[new_addrs.index(cur_obj_addr)]
            else:
                old_obj_addr = cur_obj_addr
            print(f'{name}: {old_obj_addr} -> {cur_obj_addr}')
            for child in children:
                cur_child_addr = child.getMemoryAddr()
                if cur_child_addr in new_addrs:
                    old_child_addr = old_addrs[new_addrs.index(cur_child_addr)]
                else:
                    old_child_addr = cur_child_addr
                print(f'\t{child.name}: {old_child_addr} -> {cur_child_addr}')
                pass
            
    def displayDefragHashMap(self):
        if self.debug == 0:
            return 0
        print(' ~ Defragmentation Hash Map ~ ')
        #print(f'hash table: {self.addr_table}')
        for key in self.addr_table.keys():
            value = self.addr_table[key]
            node = self.memory[value]
            name = node.name

            print(f'{name}: {key} -> {value}')

    def displayLegend(self):
        print('\n ~ Legend ~ ')
        print(' \x1b[32mgreen\x1b[0m - available for writing memory cell')
        print(' \x1b[34mblue\x1b[0m  - initial data state')
        print(' \x1b[31mred\x1b[0m   - alive data after garbage collector')


if __name__ == '__main__':

    os.system('')

    file = os.path.join(os.path.dirname(__file__), 'Examples\\two_root_nodes.mtx')
    gc_type = GCType.LINK
    defrag_type = None
    size_arg = 20
    debug_arg = 1

    if len(sys.argv) > 1:
        if '-h' in sys.argv:
            print('GCEmulator help\n Args: \n  -h\t\tPrint help message\n  -f\t\tPath to graph file\n  -t\t\tType emulation: link(l), mark(m) ')
            print('  -d\t\tDefragmentation enable(e), disable(d)')
            print('  -debug\tDebug information about graph nodes 0 - disable, 1 - enable')
            print('  -s\t\tVirtual memory size.\tExample: -s 40 (40 virtual cell\'s memory)\n\n')
            if len(sys.argv) == 2:
                sys.exit(0)
        if '-f' in sys.argv:
            if len(sys.argv)-2 >= sys.argv.index('-f'):
                file = sys.argv[sys.argv.index('-f')+1]
                print(file)
            else:
                print('Missing path in argument. Use default')
        if '-t' in sys.argv:
            if len(sys.argv)-2 >= sys.argv.index('-t'):
                gc_type_arg = sys.argv[sys.argv.index('-t')+1]
                print(f'Using {gc_type} GC method')
                if gc_type_arg == 'link' or gc_type_arg == 'l':
                    gc_type = GCType.LINK
                elif gc_type_arg == 'mark' or gc_type_arg == 'm':
                    gc_type = GCType.MARK
            else:
                print('Missing GC type in argument. Use default')
        if '-d' in sys.argv:
            if len(sys.argv)-2 >= sys.argv.index('-d'):
                defrag_type_arg = sys.argv[sys.argv.index('-d')+1]
                print(f'type defrag: {defrag_type_arg}')
                if defrag_type_arg == 'd' or defrag_type_arg == 'disable':
                    defrag_type = DefragType.DISABLE
                elif defrag_type_arg == 'e' or defrag_type_arg == 'enable':
                    defrag_type = DefragType.ENABLE
            else:
                print('Missing defragmentation in argument. Run with defragmentation.')
        if '-s' in sys.argv:
            if len(sys.argv)-2 >= sys.argv.index('-s'):
                try:
                    size_arg = int(sys.argv[sys.argv.index('-s')+1])
                    print(f'size: {size_arg}')
                except:
                    print(f'Wrong value! Use default memory size({size_arg})')
            else:
                print(f'Missing size in argument. Run using default memory size({size_arg}).')
        if '-debug' in sys.argv:
            if len(sys.argv)-2 >= sys.argv.index('-debug'):
                try:
                    debug_arg = int(sys.argv[sys.argv.index('-debug')+1])
                except:
                    debug_arg = 1
    #input()

    try:
        mApi = MemoryApi(file, gc_type, size_arg, debug_arg)
    except FileNotFoundError:
        print('!WRONG PATH!')
        print('Exiting...')
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)
    
    gc = GarbageCollector(mApi, gc_type, defrag_type)
    gc.collectGarbage()

    input()