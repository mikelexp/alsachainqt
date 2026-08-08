# Publicar una version

La release de GitHub se genera al subir un tag `vX.Y.Z`. El paquete AUR se
actualiza despues, una vez que el artefacto de GitHub esta disponible.

```bash
# Actualiza pyproject.toml, __init__.py y PKGBUILD.
make set-version VERSION=0.2.0
# o: just set-version 0.2.0

make check
git add pyproject.toml src/alsachainqt/__init__.py PKGBUILD
git commit -m "Release v0.2.0"
git tag v0.2.0
git push github main v0.2.0
```

Para una beta usá `0.2.0-beta.1` en `set-version` (también acepta el prefijo
`v`) y ese valor con `v` en el tag. El workflow la publica como pre-release de
GitHub:

```bash
make set-version VERSION=0.2.0-beta.1
git tag v0.2.0-beta.1
```

Para AUR, el `PKGBUILD` conserva ese tag como `_upstream_version` y convierte
el `pkgver` a `0.2.0beta.1`, que no contiene el separador reservado `-`.

GitHub Actions valida que el tag coincida con `pyproject.toml`, ejecuta la
suite, compila el binario onefile con Nuitka y publica
`alsachainqt-X.Y.Z-linux-x86_64.tar.gz`. El tarball contiene el binario, icono,
desktop entry, instalador y el modulo ALSA `alsachain_status`.

Cuando el workflow termine correctamente:

```bash
make aur-update
# o: just aur-update
```

El comando descarga el tarball publicado, calcula el SHA256, valida el
`PKGBUILD` con `makepkg`, genera `.SRCINFO` y sube el cambio al repositorio
`alsachainqt-bin` de AUR. Requiere una sesion autenticada de `gh`, acceso SSH a
AUR y las herramientas de empaquetado de Arch.
