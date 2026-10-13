// <copyright file="TransfersDbContext.cs" company="slskd Team">
//     Copyright (c) slskd Team. All rights reserved.
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU Affero General Public License as published
//     by the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public License
//     along with this program.  If not, see https://www.gnu.org/licenses/.
// </copyright>

// <copyright file="TransfersDbContext.cs" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
namespace slskd.Transfers
{
    using System;
    using System.Threading;
    using System.Threading.Tasks;
    using Microsoft.EntityFrameworkCore;
    using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
    using slskd.Transfers.Downloads;

    public class TransfersDbContext : DbContext
    {
        public TransfersDbContext(DbContextOptions<TransfersDbContext> options)
            : base(options)
        {
        }

        public DbSet<Transfer> Transfers { get; set; }
        public DbSet<DownloadRequest> DownloadRequests { get; set; }

        public override int SaveChanges(bool acceptAllChangesOnSuccess)
        {
            PrepareTrackedEntities();

            return base.SaveChanges(acceptAllChangesOnSuccess);
        }

        public override Task<int> SaveChangesAsync(bool acceptAllChangesOnSuccess, CancellationToken cancellationToken = default)
        {
            PrepareTrackedEntities();

            return base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
        }

        private void PrepareTrackedEntities()
        {
            var updatedAt = DateTime.UtcNow;

            // this is absolutely NOT IDEAL and will accellerate the move away from EF
            foreach (var entry in ChangeTracker.Entries<Transfer>())
            {
                if (entry.State == EntityState.Added || entry.State == EntityState.Modified)
                {
                    entry.Entity.StateDescription = entry.Entity.State.ToString();
                    entry.Entity.UpdatedAt = updatedAt;
                }
            }

            foreach (var entry in ChangeTracker.Entries<DownloadRequest>())
            {
                if (entry.State == EntityState.Added || entry.State == EntityState.Modified)
                {
                    entry.Entity.StateDescription = entry.Entity.State.ToString();
                }
            }

        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.RequestedAt)
                .HasConversion(v => v, v => DateTime.SpecifyKind(v, DateTimeKind.Utc));

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.EnqueuedAt)
                .HasConversion(v => v, v => v.HasValue ? DateTime.SpecifyKind(v.Value, DateTimeKind.Utc) : null);

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.StartedAt)
                .HasConversion(v => v, v => v.HasValue ? DateTime.SpecifyKind(v.Value, DateTimeKind.Utc) : null);

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.EndedAt)
                .HasConversion(v => v, v => v.HasValue ? DateTime.SpecifyKind(v.Value, DateTimeKind.Utc) : null);

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.NextAttemptAt)
                .HasConversion(v => v, v => v.HasValue ? DateTime.SpecifyKind(v.Value, DateTimeKind.Utc) : null);

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.UpdatedAt)
                .HasConversion(v => v, v => DateTime.SpecifyKind(v, DateTimeKind.Utc))
                .HasDefaultValueSql("CURRENT_TIMESTAMP");

            modelBuilder
                .Entity<Transfer>()
                .Property(e => e.AutoReplaceAttempts)
                .HasDefaultValue(0);

            modelBuilder
                .Entity<Transfer>()
                .Property(d => d.Direction)
                .HasConversion(new EnumToStringConverter<Soulseek.TransferDirection>());

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(
                    t => new { t.Direction, t.UpdatedAt },
                    "TransferDirectionUpdatedAt")
                .HasDatabaseName("IDX_Transfers_Direction_UpdatedAt");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(
                    t => new { t.Direction, t.UpdatedAt },
                    "TransferActionableUpdatedAt")
                .HasDatabaseName("IDX_Transfers_Actionable_UpdatedAt")
                .HasFilter("Removed = 0 AND ((State & 16) != 16 OR (State & 32) != 32)");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Removed, t.Direction })
                .HasDatabaseName("IDX_Transfers_Removed_Direction");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.RequestedAt, t.Id })
                .IsDescending(false, true, true)
                .HasDatabaseName("IDX_Transfers_Direction_RequestedAt_Id")
                .HasFilter("Removed = 0");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.EndedAt, t.RequestedAt, t.Id })
                .HasDatabaseName("IDX_Transfers_Direction_EndedAt")
                .HasFilter("EndedAt IS NOT NULL AND (State & 16) = 16 AND (State & 32) = 32");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.EndedAt, t.Id })
                .HasDatabaseName("IDX_Transfers_AutoRetry_EndedAt")
                .HasFilter(
                    "Removed = 0 AND EndedAt IS NOT NULL " +
                    "AND (State & 16) = 16 AND (State & 32) != 32 " +
                    "AND (State & 64) != 64 AND (State & 512) != 512");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => t.State)
                .HasDatabaseName("IDX_Transfers_State");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.BatchId })
                .HasDatabaseName("IDX_Transfers_Direction_BatchId")
                .HasFilter("Removed = 0");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.Username, t.Filename })
                .HasDatabaseName("IDX_Transfers_Direction_Username_Filename")
                .HasFilter("Removed = 0");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.Direction, t.UpdatedAt })
                .HasDatabaseName("IDX_Transfers_Removed_Direction_UpdatedAt")
                .HasFilter("Removed = 1 AND EndedAt IS NOT NULL");

            modelBuilder
                .Entity<Transfer>()
                .HasIndex(t => new { t.RequestId, t.Removed, t.RequestedAt })
                .HasDatabaseName("IDX_Transfers_RequestId_Current")
                .IsDescending(false, false, true);

            modelBuilder
                .Entity<DownloadRequest>()
                .Property(e => e.CreatedAt)
                .HasConversion(v => v, v => DateTime.SpecifyKind(v, DateTimeKind.Utc));

            modelBuilder
                .Entity<DownloadRequest>()
                .Property(e => e.CompletedAt)
                .HasConversion(v => v, v => v.HasValue ? DateTime.SpecifyKind(v.Value, DateTimeKind.Utc) : null);

            modelBuilder
                .Entity<DownloadRequest>()
                .Property(d => d.State)
                .HasConversion(new EnumToStringConverter<DownloadRequestState>());

            modelBuilder
                .Entity<DownloadRequest>()
                .HasIndex(r => r.State)
                .HasDatabaseName("IDX_DownloadRequests_State");

            modelBuilder
                .Entity<DownloadRequest>()
                .HasIndex(r => r.WishlistItemId)
                .HasDatabaseName("IDX_DownloadRequests_WishlistItemId");
        }
    }
}
