from fastapi import Depends
from typing import Optional
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService


class GetAgentScope:
    """
    获取当前用户智能体权限对应的查询sql语句
    """

    def __init__(
        self,
        query_alias: Optional[str] = '',
        db_alias: Optional[str] = 'db',
        graph_alias: Optional[str] = "graph_id"
    ):
        """
        获取当前用户数据权限对应的查询sql语句

        :param query_alias: 所要查询表对应的sqlalchemy模型名称，默认为''
        :param db_alias: orm对象别名，默认为'db'
        """
        self.query_alias = query_alias
        self.db_alias = db_alias
        self.graph_alias = graph_alias

    def __call__(self, current_user: CurrentUserModel = Depends(LoginService.get_current_user)):
        user_id = current_user.user.user_id
        agent_id_list = current_user.user.agent_ids
        param_sql_list = []

        if current_user.user.admin:
            param_sql_list = ['1 == 1']
        else:
            if len(agent_id_list) >= 1:
                # if len(agent_id_list) == 1:
                #     graph_ids_str = f"'{agent_id_list[0]}',"  # 单个元素时添加逗号形成元组
                # else:
                #     graph_ids_str = ', '.join([f"'{graph_id}'" for graph_id in agent_id_list])
                
                graph_ids_str = ', '.join([f"'{graph_id}'" for graph_id in agent_id_list])
                #避免当len(agent_id_list)==1时，比如agent_id_list=['abc'], graph_ids_str='abc', 
                # ('abc') 被 Python 解释为字符串而不是元组，导致 SQLAlchemy 的 in_() 方法报错 "IN expression list, SELECT construct, or bound parameter object expected"。
                graph_ids_str = "' '," + graph_ids_str 
                param_sql_list.append(
                    f"{self.query_alias}.{self.graph_alias}.in_(({graph_ids_str})) if hasattr({self.query_alias}, '{self.graph_alias}') else 1 == 0"
                )
            else:
                param_sql_list.append('1 == 0')
        param_sql_list = list(dict.fromkeys(param_sql_list))
        param_sql = f"or_({', '.join(param_sql_list)})"

        return param_sql
