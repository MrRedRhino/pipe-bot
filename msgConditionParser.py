result = False

def findComponents(condition,msg_content=None,author_name=None):
    values = []
    actions = []
    operations = []
    inString = False
    string = ''
    inInteger = False
    integer = ''

    i = 0
    while i in range(len(condition)):
        #VARIABLES
        if condition[i:i+11]=='msg_content' and not inString:
            values.append(msg_content)
            i += 11

        if condition[i:i+11]=='author_name' and not inString:
            values.append(author_name)
            i += 11

        #STRINGS & INTS & ARRAYS
        if condition[i]=='"':
            if inString:
                inString = False
                values.append(string)
                string = ''
            else:
                inString = True
        if inString:
            if condition[i]!='"':
                string += condition[i]

        if condition[i] in ['0','1','2','3','4','5','6','7','8','9']:
            if inInteger and condition[i+1] == ' ':
                integer += condition[i]
                inInteger = False
                values.append(integer)
                integer = ''
            elif inInteger == False and condition[i-1] == ' ' and not inString:
                inInteger = True
        if inInteger:
            integer += condition[i]


        ############ ACTIONS ############## ==, !=, <, !<, >, !>, <=, !<=, >=, !>=, in, !in 
        if condition[i:i+1] in ['<','>'] and not inString:
            actions.append(condition[i:i+1])
            i += 1

        if condition[i:i+2] in ['==','!=','!<','!>','<=','>=','in'] and not inString:
            actions.append(condition[i:i+2])
            i += 2

        if condition[i:i+3] in  ['!<=','!>=','!in'] and not inString:
            actions.append(condition[i:i+3])
            i += 3

        ############ OPERATIONS ############## and, or
        if condition[i:i+2]=='or' and not inString:
            operations.append('or')
            i += 3

        if condition[i:i+3]=='and' and not inString:
            operations.append('and')
            i += 3

        i += 1

    print(values)
    print(actions)
    print(operations)



findComponents('msg_content == "hallo" and author_name == "MrRedRhino"',msg_content='huhu',author_name='Autor')



