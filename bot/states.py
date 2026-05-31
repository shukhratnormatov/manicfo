from aiogram.fsm.state import State, StatesGroup


class EditStates(StatesGroup):
    waiting_new_input = State()


class EditSubStates(StatesGroup):
    waiting_name = State()
    waiting_amount = State()
    waiting_day = State()


class EditGoalStates(StatesGroup):
    waiting_name = State()
    waiting_amount = State()
