#pragma once

#include <string>
#include <vector>

struct SvdTask
{
    int task_id = 0;
    int rows = 0;
    int cols = 0;
    long long seed = 0;
    bool full_validation = false;
};

struct SvdTaskResult
{
    int task_id = 0;
    int rank = 0;
    int rows = 0;
    int cols = 0;
    long long seed = 0;
    int converged = 0;
    int passed = 0;
    int full_validation = 0;

    double bidiag_ms = 0.0;
    double gkh_ms = 0.0;
    double compute_ms = 0.0;
    double validation_ms = 0.0;
    double total_ms = 0.0;

    double recon_error = 0.0;
    double relative_recon_error = 0.0;
    double u_orth_error = 0.0;
    double v_orth_error = 0.0;
    double diagonal_error = 0.0;
    double order_error = 0.0;
    double sigma_checksum = 0.0;
};

std::vector<SvdTask> make_svd_tasks(int task_count,
                                    int rows,
                                    int cols,
                                    long long base_seed,
                                    bool full_validation);

SvdTaskResult run_svd_task(const SvdTask &task, int rank, bool verbose = false);

void write_task_results_csv(const std::string &path,
                            const std::vector<SvdTaskResult> &results);
