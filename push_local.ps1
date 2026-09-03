# push_local.ps1
# Lệnh tiện ích: Thực hiện Git Push và tự động khởi động lại Docker Compose với code mới nhất.

Write-Host "========== [1/3] Đang Git Push lên GitHub... ==========" -ForegroundColor Cyan
git push
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git push thất bại! Hủy tiến trình build Docker."
    exit $LASTEXITCODE
}

Write-Host "`n========== [2/3] Đang dừng Docker Compose hiện tại... ==========" -ForegroundColor Cyan
docker compose down

Write-Host "`n========== [3/3] Đang rebuild và khởi chạy Docker Compose mới... ==========" -ForegroundColor Cyan
# Chạy ở chế độ Detached (-d) để không chiếm dụng terminal của bạn.
# Bạn có thể xem log bằng lệnh: docker compose logs -f
docker compose up --build

Write-Host "`n✔ Hoàn thành! Mediscan AI đang chạy ngầm tại:" -ForegroundColor Green
Write-Host "- Frontend: http://localhost:3001" -ForegroundColor Yellow
Write-Host "- Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "`n* Bạn có thể xem log thời gian thực bằng lệnh: docker compose logs -f" -ForegroundColor DarkGray
