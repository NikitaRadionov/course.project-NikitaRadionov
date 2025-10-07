## Контекст
Меняем main.py, чтобы реализовать проект Media Catalog.
Меняем .github/workflows/ci.yml чтобы не было прямых пушей в main
Создаем .github/CODEOWNERS чтобы были owners у проекта


## Что сделано

Внесены изменения в ci.yml, создан CODEOWNERS
Созданы обработчики на endpoints

- `POST /users/` - Create User
- `POST /token` - Login
- `POST /media/` - Create Media
- `GET /media/` - List Media
- `GET /media/{media_id}` - Get Media
- `PUT /media/{media_id}` - Update Media
- `DELETE /media/{media_id}` - Delete Media

Написаны небольшие тесты по эндпоинтам

## Как проверял(а)
- [ ] Ветка `p02-*` → PR в `main` по шаблону (без прямых пушей).
- [ ] В PR видны осмысленные комментарии ревью и фиксы.
- [ ] Required-check `CI / build` зелёный.
- [ ] (Опц.) CODEOWNERS/автоподписанты настроены.
- [ ] (Опц.) Тег `P02` после merge.
