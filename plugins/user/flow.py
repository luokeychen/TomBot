#coding: utf-8
import os
from tombot import botcmd
from tombot import Engine

import cx_Oracle


os.environ['NLS_LANG'] = 'american_america.ZHS16GBK'


class Flow(Engine):
    '''Tom query flow id|标题\t  查询服务流程单号'''

    @botcmd
    def flow(self, message, args):
        key = args
        if self.check_contain_chinese(key):
            self.querydb(None, '%' + key + '%', message)
        else:
            self.querydb(key, '', message)

    def querydb(self, serial, title, message):
        tns = cx_Oracle.makedsn('117.27.132.23', '21001', 'itmwiki')
        conn = cx_Oracle.connect('qrycoo', 'qrycoo', tns)
        cs = conn.cursor()
        sql1 = '''
        SELECT * from
        (select
             t2.flow_id,
              coo.COO_PKP_FLOW_SQL_CFG.GETFLOWSERIAL(T1.FLOW_ID,T1.FLOW_MOD) SERIAL,
             coo.COO_PKP_FLOW_SQL_CFG.GETFLOWTYPE(T1.FLOW_MOD) FLOW_TYPE,
                    coo.COO_PKP_FLOW_SQL_CFG.GETFLOWTITLE(T1.FLOW_ID,T1.FLOW_MOD) TITLE
                    FROM coo.FLOW T1,coo.TACHE T2 where t1.flow_id = t2.flow_id) t3  where t3.SERIAL=:serial
            '''
        sql2 = '''
         SELECT * from
        (select distinct t2.flow_id,
              coo.COO_PKP_FLOW_SQL_CFG.GETFLOWSERIAL(T1.FLOW_ID,T1.FLOW_MOD) SERIAL,
            coo.COO_PKP_FLOW_SQL_CFG.GETFLOWTYPE(T1.FLOW_MOD) FLOW_TYPE,
                    coo.COO_PKP_FLOW_SQL_CFG.GETFLOWTITLE(T1.FLOW_ID,T1.FLOW_MOD) TITLE
                    FROM coo.FLOW T1,coo.TACHE T2 where t1.flow_id = t2.flow_id) t3
                    where t3.title like ''' + "'" + title + "'" + ' order by flow_type desc'
        sql2 = sql2.encode('gbk')
        url = 'http://117.27.132.23:20006/workshop/form/index.jsp?flowId='
        if serial:
            try:
                cs.execute(sql1, serial=serial)
            except cx_Oracle.DatabaseError as e:
                message.send(e.__str__())
        else:
            try:
                cs.execute(sql2)
                message.info('标题模糊查找时只显示一行结果')
            except cx_Oracle.DatabaseError as e:
                message.send(e.__str__())
        result = cs.fetchone()
        if result:
            url = url + str(result[0])
            result = gbk2utf8(' '.join(result[1:]))
            result += '\n' + url
        else:
            result = 'Noting found.'
        cs.close()
        conn.close()
        message.send(result)
        return True

    def check_contain_chinese(self, check_str):
        for ch in check_str:
            if u'\u4e00' <= ch <= u'\u9fff':
                return True
        return False
