from aiogram.fsm.state import State, StatesGroup


class EditStates(StatesGroup):
    waiting_new_input = State()
