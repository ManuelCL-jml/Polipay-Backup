import datetime as dt
from pathlib import Path
from typing import ClassVar, List, Dict, Any

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from xlwt import Worksheet


def date_format(datetime: dt.datetime):
    return datetime.strftime("%Y%m%d%H%M%S")


class ConfigExcel:
    font: ClassVar[Font] = Font
    alignment: ClassVar[Alignment] = Alignment

    def font_config(self, **kwargs):
        self.font(**kwargs)

    def alignment_config(self, **kwargs):
        self.alignment(**kwargs)


class CreateExcel:
    _location_file: ClassVar[str] = 'TMP/export_excel/transaction_status'
    _ws: ClassVar[Worksheet]
    _wb: ClassVar[Workbook]
    _config: ClassVar[ConfigExcel] = ConfigExcel()
    file_name: ClassVar[str]
    colums: ClassVar[List[str]] = ["A", "B", "C", "D", "E", "F", "G", "H", "I",
                                   "J", "K", "L", "M", "N", "O", "P", "Q", "R",
                                   "S", "T", "U", "V", "W", "X", "Y", "Z"]

    def __init__(self, query_data: List[Dict[str, Any]], razon_social_id: int):
        self._query_data = query_data
        self._razon_social_id = razon_social_id

        if len(query_data) > 0:
            self._wb = Workbook()
            self._ws = self._wb.active
            self._header()
            self._body()
            self._save()

        if len(query_data) == 0:
            raise ValueError('No hay información por exportar utilizando el filtro actual')

    # (ChrGil 2022-02-14) Construye la cabecera de excel, con las keys del diccionario
    def _header(self):
        font = self._config.font(name="Cambria", size=12, color="00000000", bold=True)
        alignment = self._config.alignment(horizontal="center", vertical="center")
        index = 0

        for key_id in self._query_data[0].keys():
            self._ws[f"{self.colums[index]}1"] = key_id
            self._ws[f"{self.colums[index]}1"].font = font
            self._ws[f"{self.colums[index]}1"].alignment = alignment
            index += 1

    # (ChrGil 2022-02-14) Construye el cuerpo del excel
    def _body(self):
        col_index = 2
        index_row = 1
        font = self._config.font(name="Arial", size=12, color="00000000")
        alignment = self._config.alignment(horizontal="left", vertical="justify")

        for _row in self._query_data:
            index_row += 1
            col_index = 0

            for _key, _value in _row.items():
                self._ws[f"{self.colums[col_index]}{index_row}"] = _value
                self._ws[f"{self.colums[col_index]}{index_row}"].font = font
                self._ws[f"{self.colums[col_index]}{index_row}"].alignment = alignment
                self._ws.column_dimensions[f"{self.colums[col_index]}"].width = 30.0
                col_index += 1

    def _save(self):
        file = f"TMP/web/ExportExcelStatus/transaction_folio{self._razon_social_id}_{date_format(dt.datetime.now())}.xlsx"
        self._wb.save(file)
        self.file_name = file
