import os
from flask import g

def get_user_db_path(user_id=None):
    """获取用户数据库路径"""
    if user_id is None:
        # 尝试从 Flask 的 g 对象获取
        try:
            from flask import g
            if hasattr(g, 'user_id'):
                user_id = g.user_id
                if hasattr(g, 'user_db_path'):
                    return g.user_db_path
        except (ImportError, RuntimeError):
            # 不在 Flask 上下文中或无法导入 Flask
            print("不在 Flask 上下文中或无法导入 Flask")
            pass
    
    # 如果有用户ID，返回用户特定数据库路径，否则返回默认路径
    if user_id:
        return os.path.join("data", f"user_{user_id}", "lancedb")
    else:
        return os.path.join("data", "lancedb")  # 默认路径