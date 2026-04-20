"""
Corredor de leitura da listagem de alunos.

Mantem a view HTTP fina enquanto concentra paginação, bootstrap de busca
e montagem do payload da página do diretório.
"""

import time

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from catalog.presentation import build_student_directory_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.student_queries import (
    _enrich_student_directory_display_students,
    build_student_directory_listing_snapshot,
    build_student_directory_support_snapshot,
)


def build_student_directory_view_context(
    *,
    request,
    context,
    base_context,
    page_size_default,
    search_bootstrap_limit,
    search_index_limit,
    clean_index_params,
    has_server_scoped_filters,
    annotate_page_students,
    serialize_search_entry,
):
    view_started_at = time.perf_counter()
    listing_started_at = time.perf_counter()
    snapshot = build_student_directory_listing_snapshot(request.GET)
    listing_duration_ms = round((time.perf_counter() - listing_started_at) * 1000, 2)
    students_queryset = snapshot["students"]
    student_count = snapshot["total_students"]
    current_role_slug = base_context["current_role"].slug
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

    class PrecountedPaginator(Paginator):
        @property
        def count(self):
            return student_count

    max_page_size = 100
    page_size_raw = request.GET.get("page_size", page_size_default)
    try:
        page_size = min(int(page_size_raw), max_page_size)
    except (ValueError, TypeError):
        page_size = page_size_default

    page_slice_started_at = time.perf_counter()
    paginator = PrecountedPaginator(students_queryset, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_slice_duration_ms = round((time.perf_counter() - page_slice_started_at) * 1000, 2)

    page_enrich_started_at = time.perf_counter()
    page_students = annotate_page_students(
        _enrich_student_directory_display_students(list(page_obj.object_list), thirty_days_ago=thirty_days_ago),
        thirty_days_ago=thirty_days_ago,
    )
    page_enrich_duration_ms = round((time.perf_counter() - page_enrich_started_at) * 1000, 2)
    page_obj.object_list = page_students
    context["students"] = page_obj

    support_started_at = time.perf_counter()
    support_snapshot = build_student_directory_support_snapshot(
        params=request.GET,
        pending_intakes_count=(base_context.get("shell_counts") or {}).get("pending_intakes"),
    )
    support_duration_ms = round((time.perf_counter() - support_started_at) * 1000, 2)

    has_server_filters = has_server_scoped_filters(request.GET)
    index_params = request.GET.copy() if has_server_filters else clean_index_params(request.GET)
    if index_params.urlencode() == request.GET.copy().urlencode():
        search_snapshot = snapshot
    else:
        search_snapshot = build_student_directory_listing_snapshot(index_params)

    search_bootstrap_started_at = time.perf_counter()
    search_page_students = annotate_page_students(
        _enrich_student_directory_display_students(
            list(search_snapshot["students"][:search_bootstrap_limit]),
            thirty_days_ago=thirty_days_ago,
        ),
        thirty_days_ago=thirty_days_ago,
    )
    search_bootstrap_duration_ms = round((time.perf_counter() - search_bootstrap_started_at) * 1000, 2)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]
    base_query_string = query_params.urlencode()
    directory_search_entries = [serialize_search_entry(student) for student in search_page_students]
    total_view_duration_ms = round((time.perf_counter() - view_started_at) * 1000, 2)

    page_payload = build_student_directory_page(
        student_count=student_count,
        students=page_obj,
        student_filter_form=snapshot["filter_form"],
        snapshot=snapshot,
        support_snapshot=support_snapshot,
        current_role_slug=current_role_slug,
        base_query_string=base_query_string,
        directory_search={
            "cache_key": index_params.urlencode() or "all",
            "refresh_token": search_snapshot.get("directory_refresh_token", ""),
            "page_url": reverse("student-search-index-page"),
            "page_size": search_index_limit,
            "total": search_snapshot.get("total_students", 0),
            "has_next": search_snapshot.get("total_students", 0) > len(search_page_students),
            "next_offset": len(search_page_students) if search_snapshot.get("total_students", 0) > len(search_page_students) else None,
            "index": directory_search_entries,
            "full_index_available": True,
        },
        performance_timing={
            "listing_snapshot_ms": listing_duration_ms,
            "listing_metrics_ms": snapshot.get("timings", {}).get("metrics_ms"),
            "listing_base_queryset_ms": snapshot.get("timings", {}).get("base_queryset_ms"),
            "listing_filter_application_ms": snapshot.get("timings", {}).get("filter_application_ms"),
            "listing_filter_form_ms": snapshot.get("timings", {}).get("filter_form_ms"),
            "support_snapshot_ms": support_duration_ms,
            "page_slice_ms": page_slice_duration_ms,
            "page_enrich_ms": page_enrich_duration_ms,
            "search_bootstrap_ms": search_bootstrap_duration_ms,
            "shell_total_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("total_ms"),
            "shell_cache_lookup_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("cache_lookup_ms"),
            "shell_build_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("build_ms"),
            "shell_overdue_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("overdue_payments_ms"),
            "shell_overdue_students_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("overdue_students_ms"),
            "shell_pending_intakes_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("pending_intakes_ms"),
            "shell_sessions_today_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("sessions_today_ms"),
            "shell_student_summary_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("student_summary_ms"),
            "shell_active_enrollments_ms": getattr(request, "_octobox_request_perf", {}).get("shell_counts", {}).get("active_enrollments_ms"),
            "auth_user_resolution_ms": getattr(request, "_octobox_request_perf", {}).get("auth_user_resolution_ms"),
            "role_navigation_ms": getattr(request, "_octobox_request_perf", {}).get("role_navigation_ms"),
            "view_total_ms": total_view_duration_ms,
        },
    )

    return attach_catalog_page_payload(
        context,
        payload_key="student_directory_page",
        payload=page_payload,
        include_sections=("context", "shell"),
    )


def build_student_search_index_payload(
    *,
    request,
    search_index_limit,
    parse_non_negative_int,
    clean_index_params,
    annotate_page_students,
    serialize_search_entry,
):
    offset = parse_non_negative_int(request.GET.get("offset"), default=0)
    index_params = clean_index_params(request.GET)
    snapshot = build_student_directory_listing_snapshot(index_params)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    next_offset = offset + search_index_limit
    students = annotate_page_students(
        _enrich_student_directory_display_students(
            list(snapshot["students"][offset:next_offset]),
            thirty_days_ago=thirty_days_ago,
        ),
        thirty_days_ago=thirty_days_ago,
    )
    total_students = snapshot.get("total_students", 0)
    return {
        "cache_key": index_params.urlencode() or "all",
        "refresh_token": snapshot.get("directory_refresh_token", ""),
        "page_size": search_index_limit,
        "total": total_students,
        "has_next": next_offset < total_students,
        "next_offset": next_offset if next_offset < total_students else None,
        "index": [serialize_search_entry(student) for student in students],
    }
