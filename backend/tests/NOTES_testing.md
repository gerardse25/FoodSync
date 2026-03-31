# Notes

- Aquest paquet manté el backend original sense editar.
- Les adaptacions perquè els tests puguin arrencar amb SQLite estan només a `backend/tests/conftest.py`.
- Els tests poden fallar perquè detecten comportaments no implementats o inconsistents del backend actual. Això és esperat i útil per reportar incidències.
- Els tests `test_register_handles_repository_lookup_failure` i `test_register_handles_repository_save_failure` s'han mantingut amb el mateix nom que en el disseny preliminar, però tècnicament simulen fallades de la capa de persistència/BD perquè aquest backend no té una capa repository separada.
