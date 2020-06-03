import pickle
import socket
import time
import dnslib


def fun(request, ip, client):
    try:
        client.sendto(request, (ip, 53))
        response, _ = client.recvfrom(2048)
        response = dnslib.DNSRecord.parse(response)
        if response.header.a == 1:
            cache[(response.questions[0].qname, response.questions[0].qtype)] = response.rr, time.time()
        if response.auth:
            cache[(response.auth[0].rname, response.auth[0].rtype)] = response.auth, time.time()
        for additional in response.ar:
            cache[(additional.rname, additional.rtype)] = [additional], time.time()
        with open('cache', 'wb') as f:
            pickle.dump(cache, f)
    except Exception:
        print("хм, хм, хм...")
        print("не удалось связаться с авторитетным сервером")


def clear_cache(cache):
    new_cache = {}
    for key in cache:
        if cache[key][0][0].ttl > time.time() - cache[key][1]:
            new_cache[key] = cache[key]
    return new_cache


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('127.0.0.1', 53))
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.settimeout(5)
try:
    with open('cache', 'rb') as f:
        cache = pickle.load(f)
except:
    cache = {}

while True:
    flag1 = False
    flag2 = False
    d = '.'
    l = -1
    new_domain = ''
    request, address = server.recvfrom(2048)
    res = dnslib.DNSRecord.parse(request)
    domain = res.questions[0].qname
    print(domain)
    str_domain = str(domain)
    if str_domain.rfind('.') == len(str_domain) - 1:
        str_domain = str_domain[:str_domain.rfind('.')]
        new_domain = str_domain
    question_type = res.questions[0].qtype
    cache = clear_cache(cache)
    if not cache.get((domain, question_type)):
        print('В кэше нет ответа на запрос, отправляем запрос авторитетному серверу')
    else:
        print('Овет взять из кэша')
    while not cache.get((domain, question_type)) and new_domain:
        if flag1:
            fun(request, '192.5.5.241', client)
            flag1 = False
            flag2 = True
        elif flag2:
            l = new_domain.rfind('.')
            d = str_domain[l+1:]
            new_domain = new_domain[:l]
            if cache.get((dnslib.DNSLabel(d), 2)):
                ns = cache.get((dnslib.DNSLabel(d), 2))[0]
                for i in ns:
                    try:
                        ip = str(cache.get((dnslib.DNSLabel(str(i.rdata)), 1))[0][0].rdata)
                        fun(request, ip, client)
                    except Exception:
                        pass
        else:
            l = new_domain.find('.')
            if not l == -1:
                d = str_domain[l+1:]
                new_domain = new_domain[l+1:]
                try:
                    if cache.get((dnslib.DNSLabel(d), 2)):
                        ns = cache.get((dnslib.DNSLabel(d), 2))[0]
                        for i in ns:
                            ip = str(cache.get((dnslib.DNSLabel(str(i.rdata)), 1))[0][0].rdata)
                            fun(request, ip, client)
                        flag2 = True
                        l = str_domain.rfind('.' + d)
                        new_domain = str_domain[:l]
                except Exception:
                    print('xm...')
            else:
                flag1 = True
                new_domain = str_domain
    if cache.get((domain, question_type)):
        header = dnslib.DNSHeader(res.header.id, q=1, a=len(cache.get((domain, question_type))[0]))
        response = dnslib.DNSRecord(header, res.questions, cache.get((domain, question_type))[0])
        server.sendto(response.pack(), address)
    else:
        print("неудалось связаться с авторитетным сервером")
