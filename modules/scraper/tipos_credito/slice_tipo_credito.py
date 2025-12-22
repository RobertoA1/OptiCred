from enum import Enum

class Slice_Tipo_Credito(Enum):
    CORPORATIVO = slice(0, 7)
    GRANDES_EMPRESAS = slice(7, 14)
    MEDIANAS_EMPRESAS = slice(14, 21)
    PEQUENAS_EMPRESAS = slice(21, 28)
    MICRO_EMPRESAS = slice(28, 37)
    CONSUMO = slice(37, 44)
    HIPOTECARIOS = slice(44, 46)