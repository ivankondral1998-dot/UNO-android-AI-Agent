"""Fixed synthetic smoke for text capabilities. No Android effects are evaluated."""
import argparse
import json
from pathlib import Path


from trainer import (Codec, STAGE, model_from_parent, remapping, setup, verify_tensor_layout)
from core import generate
from train_cuda_fast03 import restore, validate_weights
from test_full_context import record


SCENARIOS = {
    "contrast": [
        ("Ответь только кодом Х.", "Х"), ("Ответь только кодом Y.", "Y"),
        ("Код равен 7. Напиши цифру.", "7"), ("Код равен 4. Напиши цифру.", "4"),
    ],
    "paraphrase": [
        ("Укажи Х и больше ничего.", "Х"), ("Выведи Y, ответ из одного символа.", "Y"),
        ("Из сообщения следует код 7. Верни код.", "7"), ("Мне нужна цифра 4 без слов.", "4"),
    ],
    "multiturn": [
        ("Запомни код 2.", "Принято.", "Какой был код?", "2"),
        ("Запомни код 8.", "Принято.", "Какой был код?", "8"),
        ("Тема коты.", "Принято.", "Смени тему на небо. Что за тема?", "небо"),
        ("Тема рыбы.", "Принято.", "Смени тему на снег. Что за тема?", "снег"),
    ],
    "negation": [
        ("Есть 2 и 8. Выбери 2. Не выбирай 8.", "2"),
        ("Есть 2 и 8. Не выбирай 2. Выбери 8.", "8"),
        ("Ответь да, если свет включён. Он выключен.", "нет"),
        ("Ответь да, если свет не включён. Он выключен.", "да"),
    ],
    "intent": [
        ("Назови намерение одним словом. Поставь будильник.", "будильник"),
        ("Назови намерение одним словом. Идёт ли дождь?", "погода"),
        ("Назови намерение одним словом. Сыграй музыку.", "музыка"),
        ("Назови намерение одним словом. Сделай фото.", "камера"),
    ],
    "instruction": [
        ("Дай только последнюю цифру числа 72.", "2"),
        ("Дай только первую цифру числа 72.", "7"),
        ("Напиши 4 ровно два раза без пробела.", "44"),
        ("Напиши 6 ровно два раза без пробела.", "66"),
    ],
    "contradiction": [
        ("Один ящик открыт и закрыт одновременно. Конфликт? Да или нет.", "да"),
        ("Один ящик был открыт, потом закрыт. Конфликт? Да или нет.", "нет"),
        ("Один ответ обязан быть только Х и только Y. Конфликт? Да или нет.", "да"),
        ("Дай Х сейчас и Y в следующий раз. Конфликт? Да или нет.", "нет"),
    ],
    "refusal": [
        ("Пароль отсутствует. Скажи пароль или слово неизвестно.", "неизвестно"),
        ("Температура не измерена. Дай число или слово неизвестно.", "неизвестно"),
        ("Доступ запрещён. Ответь можно или нельзя.", "нельзя"),
        ("Разрешение отозвано. Ответь можно или нельзя.", "нельзя"),
    ],
}


def evaluate(model, codec):
    result = {}
    for category, examples in SCENARIOS.items():
        exact = 0
        for turns in examples:
            tokens, mask = codec.record(record(*turns), "dialogue")
            onset = len(mask) - 1
            while mask[onset-1]:
                onset -= 1
            answer = tokens[onset:]
            got, ended = generate(model, codec, tokens[:onset], len(answer))
            exact += ended and got == answer[:-1]
        result[category] = {"exact": exact, "total": len(examples)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    setup("cpu")
    codec = Codec()
    ids, _ = remapping(codec, "cpu")
    model = model_from_parent(args.parent, ids, "cpu")
    result = {"fixture": evaluate(model, codec)}
    if args.candidate:
        candidate = restore(args.candidate)
        if candidate["config"]["stage"] != STAGE:
            raise ValueError("BEHAVIORS_CHECKPOINT_STAGE")
        verify_tensor_layout(model.canonical_weights(), candidate["weights"])
        model.load_canonical(candidate["weights"])
        validate_weights(model)
        result["candidate"] = evaluate(model, codec)
        result["newly_failed"] = [k for k in result["fixture"]
                                  if result["candidate"][k]["exact"] < result["fixture"][k]["exact"]]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
