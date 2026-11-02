---
id: service-inactive
risk: prepare
scope: the systemd unit that service.status reported
title: A service is not running
title.es: Un servicio no esta en marcha
title.de: Ein Dienst laeuft nicht
title.fr: Un service n'est pas en marche
title.it: Un servizio non e in esecuzione
title.ja: サービスが動作していません
title.zh: 服务未运行
title.pt: Um serviço não está em execução
scope.es: la unidad systemd que informo service.status
scope.pt: a unidade systemd indicada por service.status
when: service.status available == true
when: service.status active == false
---
## Diagnosis
The unit is installed and systemd is available, but the unit is not active.
## Diagnosis.es
La unidad esta instalada y systemd esta disponible, pero la unidad no esta activa.
## Diagnosis.de
Die Unit ist installiert und systemd ist verfuegbar, aber die Unit ist nicht aktiv.
## Diagnosis.fr
L'unite est installee et systemd est disponible, mais l'unite n'est pas active.
## Diagnosis.it
L'unita e installata e systemd e disponibile, ma l'unita non e attiva.
## Diagnosis.ja
ユニットはインストールされ systemd も利用できますが、ユニットは有効ではありません。
## Diagnosis.zh
该单元已安装且 systemd 可用，但该单元未处于活动状态。
## Diagnosis.pt
A unidade está instalada e o systemd está disponível, mas a unidade não está ativa.
## Steps
- Read the last lines of the journal of the unit.
- Ask a person to start the unit and watch whether it stays active.
## Steps.es
- Leer las ultimas lineas del diario de la unidad.
- Pedir a una persona que arranque la unidad y vigile si se mantiene activa.
## Steps.pt
- Ler as últimas linhas do diário da unidade.
- Pedir a uma pessoa que inicie a unidade e verifique se se mantém ativa.
## Rollback
Nothing was changed by this proposal: stopping the unit again undoes a start.
## Rollback.es
Esta propuesta no cambio nada: volver a parar la unidad deshace un arranque.
## Rollback.pt
Esta proposta não alterou nada: parar novamente a unidade desfaz um arranque.
## Pre-checks
- Check that the disk of the unit has free space.
## Limits
- It does not change the configuration of the unit.
