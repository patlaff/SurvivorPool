from django.contrib import admin
from .models import League, Membership, Roster, RosterSlot, Perk


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    readonly_fields = ('joined_at',)


class RosterSlotInline(admin.TabularInline):
    model = RosterSlot
    extra = 0
    readonly_fields = ('added_at',)


class PerkInline(admin.TabularInline):
    model = Perk
    extra = 0


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'season', 'owner', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('slug', 'invite_code', 'created_at')
    inlines = [MembershipInline]


@admin.register(Roster)
class RosterAdmin(admin.ModelAdmin):
    list_display = ('user', 'league')
    list_filter = ('league',)
    inlines = [RosterSlotInline, PerkInline]
