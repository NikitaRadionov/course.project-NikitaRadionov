
| Поток/Элемент           | STRIDE                     | Риск | Контроль                                | Ссылка на NFR  | Проверка / Артефакт              |
| ----------------------- | -------------------------- | ---- | --------------------------------------- | -------------- | -------------------------------- |
| F1: HTTP Request        | S (Spoofing)               | R1   | JWT + rate limiting                     | NFR-01, NFR-05 | Unit-тест JWT + нагрузочный тест |
| F1: HTTP Request        | T (Tampering)              | R2   | HTTPS / проверка JWT                    | NFR-06         | Security review                  |
| F3: SQL Queries         | T (Tampering)              | R3   | ORM-only / запрет raw SQL               | NFR-06         | Code review SQLAlchemy           |
| F3: SQL Queries         | E (Elevation of Privilege) | R4   | RBAC / проверка прав доступа            | NFR-01         | Unit-тесты                       |
| D: SQLite DB            | I (Information Disclosure) | R5   | Права доступа / шифрование              | NFR-08         | Проверка бэкапов                 |
| F5/F6: File Save / Read | D (Denial of Service)      | R6   | Rate limiting + проверка размера файлов | NFR-03         | Нагрузочные тесты                |
| P0: FastAPI App         | R (Repudiation)            | R7   | Логирование всех операций               | NFR-02         | Structured logging               |
| F7: Backup Script       | I (Information Disclosure) | R8   | Ограниченный доступ к бэкапам           | NFR-08         | Скрипт резервного копирования    |
