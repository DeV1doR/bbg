import hashlib
import random
import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils import timezone

from django_redis import get_redis_connection
from rest_framework.authtoken.models import Token
from google.protobuf.message import Message

from protobufs import bbg1_pb2


class BBGUser(AbstractUser):

    tanks_limit = models.SmallIntegerField(default=3)

    @property
    def has_available_tank_slot(self):
        return self.tanks.count() < self.tanks_limit

    def tkeys(self):
        return [tank.tkey for tank in self.tanks.all()]

    class JSONAPIMeta:
        resource_name = "users"


class RTankProxy(object):

    @property
    def x(self):
        return self._rget().x

    @x.setter
    def x(self, value):
        self._rupdate(x=value)

    @property
    def y(self):
        return self._rget().y

    @y.setter
    def y(self, value):
        self._rupdate(y=value)

    @property
    def health(self):
        return self._rget().health

    @health.setter
    def health(self, value):
        self._rupdate(health=value)

    @property
    def speed(self):
        return self._rget().speed

    @speed.setter
    def speed(self, value):
        self._rupdate(speed=value)

    @property
    def fire_rate(self):
        return self._rget().fireRate

    @fire_rate.setter
    def fire_rate(self, value):
        self._rupdate(fireRate=value)

    @property
    def width(self):
        return self._rget().width

    @width.setter
    def width(self, value):
        self._rupdate(width=value)

    @property
    def height(self):
        return self._rget().height

    @height.setter
    def height(self, value):
        self._rupdate(height=value)

    @property
    def gun_damage(self):
        return self._rget().gun.damage

    @gun_damage.setter
    def gun_damage(self, value):
        self._rupdate(**{
            'gun': bbg1_pb2.TankGun(
                damage=int(value),
                bullets=self.gun_bullets,
                distance=self.gun_distance,
            )
        })

    @property
    def gun_bullets(self):
        return self._rget().gun.bullets

    @gun_bullets.setter
    def gun_bullets(self, value):
        self._rupdate(**{
            'gun': bbg1_pb2.TankGun(
                damage=self.gun_damage,
                bullets=int(value),
                distance=self.gun_distance,
            )
        })

    @property
    def gun_distance(self):
        return self._rget().gun.distance

    @gun_distance.setter
    def gun_distance(self, value):
        self._rupdate(**{
            'gun': bbg1_pb2.TankGun(
                damage=self.gun_damage,
                bullets=self.gun_bullets,
                distance=float(value),
            )
        })

    @property
    def direction(self):
        return self._rget().direction

    @direction.setter
    def direction(self, value):
        self._rupdate(direction=value)

    @property
    def angle(self):
        return self._rget().angle

    @angle.setter
    def angle(self, value):
        self._rupdate(angle=value)

    @property
    def nickname(self):
        return self._rget().name

    @nickname.setter
    def nickname(self, value):
        self._rupdate(name=value)

    @property
    def redis(self):
        if not hasattr(self, '_redis'):
            self._redis = get_redis_connection("default")
        return self._redis

    @property
    def thash(self):
        return "bbg:tanks"

    def save(self, **kwargs):
        super(RTankProxy, self).save(**kwargs)
        if not self._rget():
            self._rcreate()

        self.nickname = self.name

    def delete(self):
        super(RTankProxy, self).delete()
        self._rdel()

    def refresh_from_db(self):
        super(RTankProxy, self).refresh_from_db()
        self._rdrop_cache()
        self._rget()

    def recreate(self):
        self._rdel()
        self._rcreate()

    def _rupdate(self, **kw):
        self._rdrop_cache()
        tank = self._rget()
        if tank:
            for k, v in kw.items():
                if isinstance(getattr(tank, k), Message):
                    getattr(tank, k).CopyFrom(v)
                else:
                    setattr(tank, k, v)
            self.redis.hset(self.thash, self.tkey, tank.SerializeToString())
            return tank

    def _rcreate(self):
        tank = bbg1_pb2.Tank(
            id=self.pk,
            x=int(settings.GAME_CONFIG['MAP']['width'] / 2),
            y=int(settings.GAME_CONFIG['MAP']['height'] / 2),
            name=self.name
        )
        self.redis.hset(self.thash, self.tkey, tank.SerializeToString())
        return tank

    def _rdrop_cache(self):
        if hasattr(self, '_crget'):
            del self._crget

    def _rget(self):
        if not hasattr(self, '_crget'):
            buffer = self.redis.hget(self.thash, self.tkey)
            if buffer:
                self._crget = bbg1_pb2.Tank()
                self._crget.ParseFromString(buffer)
            else:
                self._crget = None
        return self._crget

    def _rdel(self):
        self.redis.hdel(self.thash, self.tkey)


def generate_rtk():
    return hashlib.md5(
        "{uid}:{salt}:{now}".format(uid=uuid.uuid4().hex,
                                    salt=random.random(),
                                    now=timezone.now().timestamp())
        .encode('utf-8')
    ).hexdigest()


class Stat(models.Model):

    DEATH = 1
    KILL = 2
    RESURECT = 3

    EVENT_CHOICES = (
        (DEATH, _("Death")),
        (KILL, _("Kill")),
        (RESURECT, _("Resurect")),
    )

    EVENT_CHOICES_LIST = [choice[0] for choice in EVENT_CHOICES]

    tank = models.ForeignKey('Tank', related_name='stats')
    event = models.IntegerField(choices=EVENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "TID: {tid}; Event: {event}" \
            .format(tid=self.tank.id, event=self.event)


class Tank(RTankProxy, models.Model):

    player = models.ForeignKey('BBGUser', related_name='tanks')
    tkey = models.CharField(max_length=32, unique=True, default=generate_rtk)
    name = models.CharField(max_length=16)
    lvl = models.BigIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class JSONAPIMeta:
        resource_name = "tanks"

    def save(self, **kwargs):
        is_created = True if self.pk else False
        if is_created and not self.player.has_available_tank_slot:
            raise Exception(_("No more available tanks for this user."))

        super(Tank, self).save(**kwargs)

    @property
    def death_count(self):
        return self.stats.filter(event=Stat.DEATH).count()

    @property
    def kill_count(self):
        return self.stats.filter(event=Stat.KILL).count()

    @property
    def resurect_count(self):
        return self.stats.filter(event=Stat.DEATH).count()

    def __str__(self):
        return "Player: {player}; Tank: {name}; LvL: {lvl}" \
            .format(player=self.player, name=self.name, lvl=self.lvl)


@receiver(post_save, sender=BBGUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
