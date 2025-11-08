from typing import Callable, List, Optional
from nIRC.irc import Context
from nIRC.logMessages import LOG_PERM_GRANTED, LOG_PERM_NO_WHITELIST, LOG_PERM_NO_REGISTER, LOG_PERM_NO_PERM
import functools
import inspect

class Permissions:
    def __init__(self, perm_list: dict[str, int], fail_callback: Optional[Callable]):
        self.perm_list= perm_list
        self.registered_users: List[str]= []
        self.fail_callback= fail_callback

    def safeguard(self, perm_lvl: int):
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                sig= inspect.signature(func)

                try:
                    bound_args= sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                except Exception as e:
                    print("FATAL BOT ERROR: error binding safeguard:", e)
                    return None

                context_arg: Context | None= None
                get_args= bound_args.arguments
                for arg in get_args:
                    if isinstance(get_args[arg], Context):
                        context_arg= get_args[arg]
                if not context_arg:
                    return None

                author= context_arg.author
                if not author in self.perm_list:
                    context_arg.logger.debug("PERM", LOG_PERM_NO_WHITELIST, user= author)
                    return await self.fail_callback(context_arg, 1) if self.fail_callback else None

                if not author in self.registered_users:
                    context_arg.logger.debug("PERM", LOG_PERM_NO_REGISTER, user= author)
                    return await self.fail_callback(context_arg, 2) if self.fail_callback else None

                if not self.perm_list[author] >= perm_lvl:
                    context_arg.logger.debug("PERM", LOG_PERM_NO_PERM, user= author, funcname= func.__name__, perm_lvl= perm_lvl)
                    return await self.fail_callback(context_arg, 3) if self.fail_callback else None

                context_arg.logger.info("PERM", LOG_PERM_GRANTED, funcname= func.__name__, perm_lvl= perm_lvl, author= author, authority= self.perm_list[author])
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def add_perm(self, user: str, perm_lvl: int):
        self.perm_list[user]= perm_lvl

    def rm_perm(self, user: str):
        old_perm_list= self.perm_list.copy()
        self.perm_list.clear()
        for usr in old_perm_list:
            if not usr== user:
                self.perm_list[usr]= old_perm_list[usr]
    
    def add_user(self, user: str):
        self.registered_users.append(user)

    def rm_user(self, user: str):
        old_reg_users= self.registered_users.copy()
        self.registered_users.clear()
        for usr in old_reg_users:
            if not usr== user:
                self.registered_users.append(usr)

async def perm_remove_user_on_leave(ctx: Context, perm: Permissions):
    perm.rm_user(ctx.author)
