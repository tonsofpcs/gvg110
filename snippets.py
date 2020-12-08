"Useful snippets, not used currently"

def orlist(list1, list2):
    return [l1 | l2 for l1,l2 in zip(list1,list2)]

def andlist(list1, list2):
    return [l1 & l2 for l1,l2 in zip(list1,list2)]

def xorlist(list1, list2):
    return [l1 ^ l2 for l1,l2 in zip(list1,list2)]

def orbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        result[i] |= b
    return bytes(result)

def andbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        print(i, result[i], b)
        result[i] &= b
    return bytes(result)

def xorbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        result[i] ^= b
    return bytes(result)
