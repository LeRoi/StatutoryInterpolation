# StatutoryInterpolation
# Diff.py
import os
import re
import string
import codecs
from HTMLParser import HTMLParser
from collections import OrderedDict


class Division:
    # TODO: Handle writing of \xef\xbf\xbd characters from ver1999.htm
    def __init__(self, name, section, count, parent):
        self.name = name
        self.section = section
        self.subs = []
        self.count = count
        self.parent = parent

    def div_write(self, indent, output):
        if self.section == '':
            for i in range(0, indent):
                output.write('\t')
            output.write('<division name="'+self.name+'" section="'+self.section+'" count='+str(self.count) + '>\n')
        for sub in self.subs:
            if type(sub) is tuple:
                if not re.search('^\s*$', sub[1]):
                    for i in range(0, indent+1):
                        output.write('\t')
                    output.write('<revision date='+sub[0]+'>'+sub[1]+'</revision>\n')
            elif sub.section != '':
                sub.div_write(indent+1, output)
            else:
                sub.div_write(indent+1, output)
        if self.section == '':
            for i in range(0, indent):
                output.write('\t')
            output.write('</division>\n')

    def add_sub(self, name, section, count):
        self.subs.append(Division(name, section, count, self))

    def add_text(self, text, date, hitspecial):
        if hitspecial and self.subs:
            if type(self.subs[-1]) is tuple:
                newtext = self.subs[-1][1] + text
                self.subs.pop()
                self.subs.append((date, newtext))
            else:
                self.subs.append((date, text))
        else:
            self.subs.append((date, text))

    def sub_count(self):
        return len(self.subs)

    def sub_list(self):
        if self.section != '':
            sublist = [self.section]
            for sub in self.subs:
                if type(sub) is not tuple:
                    sublist = sublist + sub.sub_list()
            return sublist
        else:
            return []


class USCParser(HTMLParser):
    # TODO: Handle tables/divs
    def __init__(self):
        HTMLParser.__init__(self)
        self.start = 0
        self.diffdict = OrderedDict()
        self.codestruc = Division('complete', '/', 0, None)
        self.active = self.codestruc
        self.path = ''
        self.date = ''
        self.section = ''
        self.hitspecial = 0
        self.htmlclass = ''
        self.sub = 0

    def handle_entityref(self, name):
        self.active.add_text(self.unescape('&' + name + ';'), self.date, 1)
        self.hitspecial = 1

    def handle_starttag(self, tag, attrs):
        # TODO: Improve on wrong assumption that subdivisions are properly classified with the -#em html class
        if not (tag.startswith('h') or tag.startswith('p')):
            self.hitspecial = 1
        for item in attrs:
            if item[0] == 'class':
                self.htmlclass = item[1]
                if item[1].endswith('em'):
                    em = int(item[1].split('em')[-2][-1])
                else:
                    em = 0
                if self.sub == em and em > 0:
                    self.active = self.active.parent
                    index = self.active.sub_count()
                    subs = ''
                    for i in range(0, self.sub):
                        subs = subs + 'sub'
                    self.active.add_sub(subs + 'division', '', index)
                    self.active = self.active.subs[index]
                elif self.sub < em:
                    while self.sub < em:
                        index = self.active.sub_count()
                        subs = ''
                        for i in range(0, em):
                            subs = subs + 'sub'
                        self.active.add_sub(subs + 'division', '', index)
                        self.active = self.active.subs[index]
                        self.sub += 1
                else:
                    while self.sub > em:
                        self.active = self.active.parent
                        self.sub -= 1

    def handle_endtag(self, tag):
        if not (tag.startswith('h') or tag.startswith('p')):
            self.hitspecial = 1
        else:
            self.hitspecial = 0

    def handle_data(self, data):
        for dstr in re.findall(r"\w+|[^\w\s]", data, re.UNICODE):
            if self.start:
                self.diffdict[self.path].append(dstr)

        if self.start:
            if not re.search('^\s*$', data):
                self.active.add_text(data.rstrip(), self.date, self.hitspecial)
            self.hitspecial = 0

    def handle_comment(self, data):
        if 'itempath' in data:
            self.path = data.split(' itempath:')[1].rstrip()
            self.start = 1
            if self.path not in self.diffdict:
                self.diffdict[self.path] = []

            bottom = self.path.split('/')[-1]
            if 'Sec.' in bottom:
                name = 'section'
            elif 'Secs.' in bottom:
                name = 'sections'
            elif 'SUBCHAPTER' in bottom:
                name = 'subchapter'
            elif 'CHAPTER' in bottom:
                name = 'chapter'
            elif 'PART' in bottom:
                name = 'part'
            else:
                name = 'title'
            while self.active.parent and len(self.path.split('/')) <= len(self.active.section.split('/')):
                self.active = self.active.parent
            index = self.active.sub_count()
            self.active.add_sub(name, self.path, index)
            self.active = self.active.subs[index]
        if 'currentthrough' in data:
            self.date = data.split('currentthrough:')[1][:8]
        if 'field-start' in data:
            index = self.active.sub_count()
            self.active.add_sub(data.split('field-start:')[1].rstrip(), '', index)
            self.active = self.active.subs[index]
        if 'field-end' in data:
            self.active = self.active.parent
            while self.sub > 0:
                self.active = self.active.parent
                self.sub -= 1

    def get_diffdict(self):
        return self.diffdict

    def get_codestruc(self):
        return self.codestruc


class Diff:
    def __init__(self, path='', date='', t='', pos=0, add='', remove=''):
        self.path = path
        self.date = date
        self.type = t
        self.pos = pos
        self.add = add
        self.remove = remove

    def get_csv(self):
        return '#'.join((self.path, self.date, str(self.type), str(self.pos), self.add, self.remove))


class DivisionDiff:
    def __init__(self, d1, d2, key):
        # TODO: Order q1, q2, dq such that diff is properly ordered.
        self.diffs = []
        self.subdivs = []

        l1 = []
        l2 = []
        sd1 = OrderedDict()
        sd2 = OrderedDict()
        q1 = []
        q2 = []

        # Matters which version goes first
        for k in d1:
            if k.endswith(key):
                for item in d1[k]:
                    l1.append((k, item))
            elif 'CHAPTER 44/Sec. 922' in k:
                continue
            elif key + '/' in k and '/' not in k.split(key + '/')[1]:
                q1.append(('', k))
                sd1[k] = list(d1[k])
            elif key + '/' in k:
                sd1[k] = list(d1[k])
        for k in d2:
            if k.endswith(key):
                for item in d2[k]:
                    l2.append((k, item))
            elif 'CHAPTER 44/Sec. 922' in k:
                continue
            elif key + '/' in k and '/' not in k.split(key + '/')[1]:
                q2.append(('', k))
                sd2[k] = list(d2[k])
            elif key + '/' in k:
                sd2[k] = list(d2[k])

        self.diffs = diff(l1, l2)

        dq = diff(q1, q2)
        i = 0
        j = 0

        while i < len(q1) or j < len(dq):
            if j < len(dq):
                if dq[j].split('#')[2] != '+':
                    j += 1
                elif int(dq[j].split('#')[3]) <= i:
                    self.subdivs.append(DivisionDiff(sd1, sd2, dq[j].split('#')[4][1:-1]))
                    j += 1
                else:
                    if i < len(q1):
                        self.subdivs.append(DivisionDiff(sd1, sd2, q1[i][1]))
                    i += 1
            else:
                self.subdivs.append(DivisionDiff(sd1, sd2, q1[i][1]))
                i += 1

    def totaldiff(self):
        ld = list(self.diffs)
        for div in self.subdivs:
            ld.extend(div.totaldiff())
        return ld

    def td_write(self, output):
        for item in self.totaldiff():
            output.write(item + '\n')


def diff(s1, s2):
    """Apply the Myers algorithm to generate a diff chart for 2 strings or 2 lists of words."""
    """The lists are expected to be tuples of the form (path to the word in the statute, word)"""
    # TODO: Implement Copy Functionality to Supplement Insertions and Deletions.
    # Initialize MAX and V as laid out in Figure 2 of the Myers Paper
    # Also initialize 2D array for tracking the optimal path to each node
    n = len(s1)
    m = len(s2)
    maxEdit = n + m
    if maxEdit == 0:
        return []
    V = {maxEdit+1: 0}
    trace = []
    done = 0

    for D in range(0, maxEdit+1):
        if done == 1:
            break

        trace.append(dict(V))

        for k in range(-D, D+1, 2):
            if k+1+maxEdit in V:
                vplus = V[k+1+maxEdit]
            else:
                vplus = -1
            if k-1+maxEdit in V:
                vminus = V[k-1+maxEdit]
            else:
                vminus = -1
            if k == -D or (k != D and vminus < vplus):
                x = vplus
                y = x - k
            else:
                x = vminus + 1
                y = x - k
            while x < n and y < m:
                if s1[x] == s2[y]:
                    x += 1
                    y += 1
                else:
                    break
            V[k+maxEdit] = x
            if x >= n and y >= m:
                done = 1
                break

    x = n
    y = m
    backward = []

    for v in reversed(trace):
        k = x - y
        if k+1+maxEdit in v:
            vplus = v[k+1+maxEdit]
        else:
            vplus = -1
        if k-1+maxEdit in v:
            vminus = v[k-1+maxEdit]
        else:
            vminus = -1
        if k == -D or (k != D and vminus < vplus):
            pk = k + 1
        else:
            pk = k - 1
        if pk+maxEdit in v:
            vset = v[pk+maxEdit]
        else:
            vset = -1
        px = vset
        py = px - pk

        while x > px and y > py:
            x = x - 1
            y = y - 1

        if x > px >= 0:
            if type(s1[px]) is tuple:
                backward.append(Diff(s1[px][0], '', '-', px, '""', '"' + s1[px][1] + '"').get_csv())
            else:
                backward.append(Diff('', '', '-', px, '""', '"' + s1[px] + '"').get_csv())
        elif y > py >= 0:
            if type(s2[py]) is tuple:
                backward.append(Diff(s2[py][0], '', '+', py, '"' + s2[py][1] + '"', '""').get_csv())
            else:
                backward.append(Diff('', '', '+', py, '"' + s2[py] + '"', '""').get_csv())

        x = px
        y = py

    path = list(reversed(backward))
    return path


def merge(s1, diff):
    """Given a first list of words and the resulting diff, generate the merged list of words."""
    i = 0
    j = 0
    lmerge = []

    while i < len(s1) or j < len(diff):
        if j < len(diff):
            if diff[j].split('#')[2] != '+':
                j += 1
            elif int(diff[j].split('#')[3]) <= i:
                lmerge.append(diff[j].split('#')[4][1:-1])
                j += 1
            else:
                if i < len(s1):
                    lmerge.append(s1[i])
                i += 1
        else:
            lmerge.append(s1[i])
            i += 1
    return lmerge


def parse(fname):
    """Parse an HTML file for a title of the US Code into a dictionary of lists of words organized by path."""
    # TODO: Preserve structure and Added Granularity
    readfile = open(fname, 'r')
    parser = USCParser()
    # parser.feed(parser.unescape(readfile.read()))
    parser.feed(readfile.read())
    return parser.get_diffdict()


def divisiondiff(fname1, fname2, div, num):
    """Given HTML docs for two US Code Versions, get a diff for the piece given by the division and the number."""
    # TODO: How Do We Handle Changes to Section Number Between Versions?
    # TODO: Handle Section Ranges (# To #) (Also, getting too much text, all sections in range)
    d1 = parse(fname1)
    d2 = parse(fname2)

    l1 = []
    l2 = []

    if div == 'section':
        for key in d1:
            if key.endswith('Sec. ' + str(num)):
                # l1 = list(d1[key])
                for item in d1[key]:
                    l1.append((key, item))
            elif len(key.split('Sec. ' + str(num))) > 1:
                if key.split('Sec. ' + str(num))[1] in string.letters:
                    for item in d1[key]:
                        l1.append((key, item))
            elif 'Secs. ' in key:
                if (' ' + str(num) + ' ') in key or (' ' + str(num) + ',') in key or key.endswith(' ' + str(num)):
                    # l1 = list(d1[key])
                    for item in d1[key]:
                        l1.append((key, item))
                elif ' to ' in key:
                    if int(key.split('to')[0].split()[-1]) <= num <= int(key.split('to')[1].rstrip().lstrip()):
                        for item in d1[key]:
                            l1.append((key, item))
        for key in d2:
            if key.endswith('Sec. ' + str(num)):
                # l2 = list(d2[key])
                for item in d2[key]:
                    l2.append((key, item))
            elif len(key.split('Sec. ' + str(num))) > 1:
                if key.split('Sec. ' + str(num))[1] in string.letters:
                    for item in d2[key]:
                        l2.append((key, item))
            elif 'Secs. ' in key:
                if (' ' + str(num) + ' ') in key or (' ' + str(num) + ',') in key or key.endswith(' ' + str(num)):
                    # l2 = list(d2[key])
                    for item in d2[key]:
                        l2.append((key, item))
                elif ' to ' in key:
                    if int(key.split('to')[0].split()[-1]) <= num <= int(key.split('to')[1].rstrip().lstrip()):
                        for item in d2[key]:
                            l2.append((key, item))
    # The remaining logic assumes a structure akin to Title 18 (Title > Part > Chapter > Section)
    elif div == 'chapter':
        for key in d1:
            if ('CHAPTER ' + str(num) + '/') in key or key.endswith('Chapter ' + str(num)):
                # l1.extend(d1[key])
                for item in d1[key]:
                    l1.append((key, item))
            elif len(key.split('CHAPTER ' + str(num))) > 1:
                if key.split('CHAPTER ' + str(num))[1] in string.letters:
                    for item in d1[key]:
                        l1.append((key, item))
                elif len(key.split('CHAPTER ' + str(num))[1]) > 1:
                    if key.split('CHAPTER ' + str(num))[1][0] in string.letters:
                        for item in d1[key]:
                            l1.append((key, item))
        for key in d2:
            if ('CHAPTER ' + str(num) + '/') in key or key.endswith('Chapter ' + str(num)):
                # l2.extend(d2[key])
                for item in d2[key]:
                    l2.append((key, item))
            elif len(key.split('CHAPTER ' + str(num))) > 1:
                if key.split('CHAPTER ' + str(num))[1] in string.letters:
                    for item in d2[key]:
                        l2.append((key, item))
                elif len(key.split('CHAPTER ' + str(num))[1]) > 1:
                    if key.split('CHAPTER ' + str(num))[1][0] in string.letters:
                        for item in d2[key]:
                            l2.append((key, item))
    elif div == 'part':
        for key in d1:
            if ('PART ' + num + '/') in key or key.endswith('PART ' + str(num)):
                # l1.extend(d1[key])
                for item in d1[key]:
                    l1.append((key, item))
        for key in d2:
            if ('PART ' + num + '/') in key or key.endswith('PART ' + str(num)):
                # l2.extend(d2[key])
                for item in d2[key]:
                    l2.append((key, item))

    return diff(l1, l2)


def doc_diff(fname1, fname2, output):
    """Given HTML docs for 2 US Code versions, generate the diff of the 2 versions."""
    d1 = parse(fname1)
    d2 = parse(fname2)

    doc = DivisionDiff(d1, d2, '/180')
    doc.td_write(output)


def code_produce(fnames, output):
    """Given a list of versions of the US Code, write a structured compilation of the versions."""
    codelist = []
    doclist = []
    for fname in fnames:
        myfile = open(fname, 'r')
        parser = USCParser()
        parser.feed(myfile.read())
        codelist.append((fname.split('\\')[-1], parser.get_codestruc()))
        doclist.append(parser.get_codestruc().sub_list())
    if len(doclist) > 0:
        dmerge = list(doclist[0])
        for i in range(1, len(doclist)):
            ddiff = diff(dmerge, doclist[i])
            dmerge = merge(dmerge, ddiff)

        mergedict = {}
        check_dict = {}
        for div in dmerge:
            mergedict[div] = []
            check_dict[div] = 0

        for struc in codelist:
            queue = [struc[1]]
            while queue:
                mydiv = queue[0]
                if mydiv.section in mergedict:
                    mergedict[mydiv.section].append(mydiv)
                for sub in mydiv.subs:
                    if type(sub) is not tuple:
                        queue.append(sub)
                del queue[0]

        for div in dmerge:
            code_write(div, mergedict, check_dict, output)


def code_write(div, div_dict, check_dict, output):
    # TODO: Handle count for major divisions
    if check_dict[div] == 0:
        check_dict[div] = 1
        indent = len(div.split('/')) - 2
        for i in range(0, indent):
            output.write('\t')
        output.write('<division name="'+div_dict[div][0].name+'" section='+div+'" count='+'' + '>\n')

        subdivs = []
        for year in div_dict[div]:
            for sub in year.subs:
                if type(sub) is tuple:
                    if not re.search('^\s*$', sub[1]):
                        for i in range(0, indent + 1):
                            output.write('\t')
                        output.write('<revision date=' + sub[0] + '>' + sub[1] + '</revision>\n')
                elif sub.section == '':
                    sub.div_write(indent+1, output)
                else:
                    subdivs.append(sub.section)

        for subdiv in subdivs:
            code_write(subdiv, div_dict, check_dict, output)

        for i in range(0, indent):
            output.write('\t')
        output.write('</division>\n')


if __name__ == '__main__':
    mydir = os.path.dirname(__file__)
    fn1 = os.path.join(mydir, '..', 'Title 18', 'ver2012.htm')
    fn2 = os.path.join(mydir, '..', 'Title 18', 'ver2016.htm')
    # fn2 = os.path.join(mydir, '..', 'Title 18', 'Test', 'ch1.htm')
    fout = codecs.open(mydir + '/../diffs/Title 18/test', 'w', 'utf-8')
    code_produce([fn1, fn2], fout)
    # doc_diff(fn1, fn2, fout)
