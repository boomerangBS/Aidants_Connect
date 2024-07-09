from enum import IntEnum, unique

@unique
class HabilitationFormStep(IntEnum):
    ISSUER = 1
    ORGANISATION = 2
    PERSONNEL = 3
    SUMMARY = 4

    @classmethod
    def size(cls):
        return len(cls)
